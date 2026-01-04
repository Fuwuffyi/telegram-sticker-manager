import io
import zipfile
import asyncio
import shutil
import time
from pathlib import Path

from flask import Flask, Response, jsonify, make_response, render_template, request, send_from_directory, send_file
from rapidfuzz import fuzz

from src.config import DATABASE_FILE, DOWNLOAD_DIR
from src.database import CustomPackSticker, Database, StickerPackRecord, StickerRecord, StickerSearchResult
from src.bot.update_service import UpdateService
from src.web.signal_uploader import upload_custom_pack_to_signal, upload_telegram_pack_to_signal

app: Flask = Flask(__name__)
db: Database = Database(DATABASE_FILE)
update_service: UpdateService = UpdateService(
    download_dir=Path(DOWNLOAD_DIR),
    db=db,
)

def fuzzy_search_packs(query: str, packs: list[StickerPackRecord]) -> list[StickerPackRecord]:
    if not query:
        return packs
    results: list[tuple[StickerPackRecord, float]] = []
    for pack in packs:
        # Search in pack name and title
        name_score: float = max(
            fuzz.partial_ratio(query.lower(), pack['name'].lower()),
            fuzz.partial_ratio(query.lower(), pack['title'].lower())
        )
        # Search in artist
        artist_score: float = fuzz.partial_ratio(query.lower(), pack['artist'].lower())
        # Take the best score
        score: float = max(name_score, artist_score)
        if score > 40:
            results.append((pack, score))
    # Sort by score
    results.sort(key=lambda x: x[1], reverse=True)
    return [r[0] for r in results]

def fuzzy_search_stickers(query: str, stickers: list[StickerSearchResult]) -> list[StickerSearchResult]:
    if not query:
        return stickers
    results: list[tuple[StickerSearchResult, float]] = []
    for sticker in stickers:
        # Calculate scores for different fields
        pack_score: float = max(
            fuzz.partial_ratio(query.lower(), sticker['pack_name'].lower()),
            fuzz.partial_ratio(query.lower(), sticker['pack_title'].lower())
        )
        artist_score: float = fuzz.partial_ratio(query.lower(), sticker['artist'].lower())
        emoji_score: float = (
            fuzz.partial_ratio(query.lower(), sticker['emoji'].lower())
            if sticker['emoji'] else 0
        )
        # Take the best score
        score: float = max(pack_score, artist_score, emoji_score)
        if score > 40:
            results.append((sticker, score))
    # Sort by score
    results.sort(key=lambda x: x[1], reverse=True)
    return [r[0] for r in results]

@app.route('/')
def index() -> str:
    return render_template('packs.html')

@app.route('/stickers')
def stickers_page() -> str:
    return render_template('stickers.html')

@app.route('/custom-packs')
def custom_packs_page() -> str:
    return render_template('custom_packs.html')

@app.route('/api/packs/search')
def search_packs() -> Response:
    query: str = request.args.get('q', '')
    page: int = int(request.args.get('page', 1))
    per_page: int = int(request.args.get('per_page', 100000))
    packs, _ = db.search_sticker_packs(query, page=1, per_page=100000)
    filtered_packs: list[StickerPackRecord] = fuzzy_search_packs(query, packs)
    # Apply pagination
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_packs = filtered_packs[start_idx:end_idx]
    # Get thumbnails for each pack
    packs_with_thumbnails = []
    for pack in paginated_packs:
        thumbnails: list[StickerRecord] = db.get_pack_thumbnail_stickers(pack['name'], limit=4)
        pack_dict = dict(pack)
        pack_dict['thumbnails'] = [
            {
                'file_path': s['file_path'],
                'emoji': s['emoji']
            }
            for s in thumbnails
        ]
        # Check if pack needs update
        pack_dict['needs_signal_update'] = (
            pack.get('signal_uploaded_at') is not None and
            pack.get('last_update', 0) > pack.get('signal_uploaded_at', 0)
        )
        packs_with_thumbnails.append(pack_dict)
    return jsonify({
        'packs': packs_with_thumbnails,
        'total': len(filtered_packs),
        'page': page,
        'per_page': per_page,
        'has_more': end_idx < len(filtered_packs)
    })

@app.route('/api/packs/<pack_name>')
def get_pack(pack_name: str) -> tuple[Response, int] | Response:
    pack_info: StickerPackRecord | None = db.get_sticker_pack(pack_name)
    if not pack_info:
        return jsonify({'error': 'Pack not found'}), 404
    page: int = int(request.args.get('page', 1))
    per_page: int = int(request.args.get('per_page', 100))
    stickers, total = db.get_pack_stickers(pack_name, page, per_page)
    needs_signal_update: bool = (
        pack_info.get('signal_uploaded_at') is not None and
        pack_info.get('last_update', 0) > pack_info.get('signal_uploaded_at', 0)
    )
    response_pack = {
        'name': pack_info['name'],
        'title': pack_info['title'],
        'artist': pack_info['artist'],
        'last_update': pack_info['last_update'],
        'sticker_count': pack_info['sticker_count'],
        'signal_url': pack_info.get('signal_url'),
        'signal_uploaded_at': pack_info.get('signal_uploaded_at'),
        'needs_signal_update': needs_signal_update,
        'used_in_custom_packs': pack_info.get('used_in_custom_packs', False),
        'stickers': [dict(s) for s in stickers],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }
    return jsonify(response_pack)

@app.route('/api/packs/<pack_name>', methods=['DELETE'])
def delete_pack(pack_name: str) -> tuple[Response, int] | Response:
    try:
        if not db.get_sticker_pack(pack_name):
            return jsonify({'error': 'Pack not found'}), 404
        # Delete from database
        success: bool = db.delete_sticker_pack(pack_name)
        if not success:
            return jsonify({'error': 'Failed to delete pack from database'}), 500
        # Delete pack directory and files
        pack_dir: Path = DOWNLOAD_DIR / pack_name
        if pack_dir.exists():
            try:
                shutil.rmtree(pack_dir)
            except Exception as e:
                # Pack deleted from DB but files remain
                app.logger.warning(f"Deleted pack from DB but failed to delete files: {e}")
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error deleting pack: {e}", exc_info=True)
        return jsonify({'error': f'Internal error: {str(e)}'}), 500

@app.route('/api/packs/<pack_name>/artist', methods=['POST'])
def update_pack_artist(pack_name: str) -> tuple[Response, int] | Response:
    if not db.get_sticker_pack(pack_name):
        return jsonify({'error': 'Pack not found'}), 404
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400
    artist: str = data.get('artist', 'Unclassified')
    success: bool = db.update_pack_artist(pack_name, artist)
    if success:
        return jsonify({'success': True, 'artist': artist})
    return jsonify({'error': 'Failed to update artist'}), 500

@app.route('/api/packs/<pack_name>/emoji', methods=['POST'])
def update_sticker_emoji(pack_name: str) -> tuple[Response, int] | Response:
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request'}), 400
        unique_id: str = data.get('unique_id', '')
        emojis: str = data.get('emojis', '')
        if not unique_id:
            return jsonify({'error': 'unique_id required'}), 400
        success: bool = db.update_sticker_emoji(pack_name, unique_id, emojis)
        if success:
            return jsonify({'success': True, 'unique_id': unique_id, 'emojis': emojis})
        return jsonify({'error': 'Failed to update emoji - sticker not found'}), 404
    except Exception as e:
        app.logger.error(f"Error updating emoji: {e}", exc_info=True)
        return jsonify({'error': f'Internal error: {str(e)}'}), 500

@app.route('/api/packs/<pack_name>/upload-signal', methods=['POST'])
def upload_pack_to_signal(pack_name: str) -> tuple[Response, int] | Response:
    try:
        pack_info: StickerPackRecord | None = db.get_sticker_pack(pack_name)
        if not pack_info:
            return jsonify({'error': 'Pack not found'}), 404
        # Run async upload
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            signal_url: str | None = loop.run_until_complete(upload_telegram_pack_to_signal(db, pack_name))
        finally:
            loop.close()
        if not signal_url:
            return jsonify({'error': 'Failed to upload to Signal'}), 500
        # Update database with Signal URL
        uploaded_at: int = int(time.time())
        _ = db.update_pack_signal_url(pack_name, signal_url, uploaded_at)
        return jsonify({
            'success': True,
            'signal_url': signal_url,
            'uploaded_at': uploaded_at
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        app.logger.error(f"Error uploading to Signal: {e}", exc_info=True)
        return jsonify({'error': f'Internal error: {str(e)}'}), 500

@app.route('/api/packs/update-all', methods=['POST'])
def update_all_packs():
    try:
        loop = asyncio.new_event_loop()
        try:
            results: dict[str, bool] = loop.run_until_complete(
                update_service.update_all_packs()
            )
        finally:
            loop.close()
        return jsonify({
            'success': True,
            'results': results,
            'updated': sum(v for v in results.values()),
            'failed': sum(not v for v in results.values()),
        })
    except Exception as e:
        app.logger.error("Bulk update failed", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500

@app.route('/api/packs/<pack_name>/update', methods=['POST'])
def update_single_pack(pack_name: str):
    try:
        loop = asyncio.new_event_loop()
        try:
            success: bool = loop.run_until_complete(
                update_service.update_pack(pack_name)
            )
        finally:
            loop.close()
        if not success:
            return jsonify({
                'success': False,
                'pack': pack_name,
                'error': 'Update failed',
            }), 500
        return jsonify({
            'success': True,
            'pack': pack_name,
        })
    except Exception as e:
        app.logger.error("Pack update failed", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500

@app.route('/api/stickers/search')
def search_stickers() -> Response:
    query: str = request.args.get('q', '')
    stickers, total = db.search_stickers(query, page=1, per_page=100000)
    filtered_stickers: list[StickerSearchResult] = fuzzy_search_stickers(query, stickers)
    results: list[dict[str, str | dict[str, str]]] = [
        {
            'pack_name': s['pack_name'],
            'pack_title': s['pack_title'],
            'artist': s['artist'],
            'sticker': {
                'file_unique_id': s['file_unique_id'],
                'file_path': s['file_path'],
                'emoji': s['emoji'],
            },
            'emoji': s['emoji']
        }
        for s in filtered_stickers
    ]
    return jsonify({
        'stickers': results,
        'total': total
    })

@app.route('/api/custom-packs', methods=['GET'])
def get_custom_packs() -> Response:
    packs_with_counts, total = db.get_all_custom_packs(page=1, per_page=100000)
    result = {}
    for pack, count in packs_with_counts:
        # Get first 2 stickers as thumbnails
        thumbnails, _ = db.get_custom_pack_stickers(pack['name'], page=1, per_page=2)
        # Check if pack needs update
        needs_signal_update: bool = (
            pack.get('signal_uploaded_at') is not None and
            pack.get('last_modified', 0) > pack.get('signal_uploaded_at', 0)
        )
        result[pack['name']] = {
            'name': pack['name'],
            'title': pack['title'],
            'signal_url': pack.get('signal_url'),
            'signal_uploaded_at': pack.get('signal_uploaded_at'),
            'needs_signal_update': needs_signal_update,
            'sticker_count': count,
            'thumbnails': [
                {
                    'pack_name': s['pack_name'],
                    'file_path': s['file_path'],
                    'emoji': s['emoji']
                }
                for s in thumbnails
            ]
        }
    return jsonify({
        'packs': result,
        'total': total
    })

@app.route('/api/custom-packs', methods=['POST'])
def create_custom_pack() -> tuple[Response, int]:
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'Invalid request'}), 400
    pack_name: str = data['name']
    pack_title: str = data.get('title', pack_name)
    success: bool = db.create_custom_pack(pack_name, pack_title)
    if success:
        return jsonify({'success': True, 'pack': {'name': pack_name, 'title': pack_title}}), 201
    return jsonify({'error': 'Pack already exists'}), 400

@app.route('/api/custom-packs/<pack_name>', methods=['GET'])
def get_custom_pack(pack_name: str) -> tuple[Response, int] | Response:
    pack = db.get_custom_pack(pack_name)
    if not pack:
        return jsonify({'error': 'Pack not found'}), 404
    # Get stickers
    stickers, total = db.get_custom_pack_stickers(pack_name, page=1, per_page=100000)
    needs_signal_update: bool = (
        pack.get('signal_uploaded_at') is not None and
        pack.get('last_modified', 0) > pack.get('signal_uploaded_at', 0)
    )
    return jsonify({
        'name': pack['name'],
        'title': pack['title'],
        'signal_url': pack.get('signal_url'),
        'signal_uploaded_at': pack.get('signal_uploaded_at'),
        'needs_signal_update': needs_signal_update,
        'stickers': [dict(s) for s in stickers],
        'total': total
    })

@app.route('/api/custom-packs/<pack_name>', methods=['PUT'])
def update_custom_pack(pack_name: str) -> tuple[Response, int] | Response:
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request'}), 400
        if not db.get_custom_pack(pack_name):
            return jsonify({'error': 'Pack not found'}), 404
        title: str = data.get('title', '')
        stickers_data: list[dict[str, str]] = data.get('stickers', [])
        stickers: list[CustomPackSticker] = [
            CustomPackSticker(
                pack_name=s.get('pack_name', ''),
                pack_title=s.get('pack_title', ''),
                file_unique_id=s.get('file_unique_id', ''),
                file_path=s.get('file_path', ''),
                emoji=s.get('emoji', ''),
                display_order=0  # Will be set by database
            )
            for s in stickers_data
        ]
        success: bool = db.update_custom_pack(pack_name, title, stickers)
        if success:
            return jsonify({'success': True, 'pack': {'name': pack_name, 'title': title}})
        return jsonify({'error': 'Failed to update pack'}), 500
    except Exception as e:
        app.logger.error(f"Error updating custom pack: {e}", exc_info=True)
        return jsonify({'error': f'Internal error: {str(e)}'}), 500

@app.route('/api/custom-packs/<pack_name>/upload-signal', methods=['POST'])
def upload_custom_pack_to_signal_endpoint(pack_name: str) -> tuple[Response, int] | Response:
    try:
        pack_info = db.get_custom_pack(pack_name)
        if not pack_info:
            return jsonify({'error': 'Pack not found'}), 404
        # Run async upload
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            signal_url = loop.run_until_complete(
                upload_custom_pack_to_signal(db, pack_name)
            )
        finally:
            loop.close()
        if not signal_url:
            return jsonify({'error': 'Failed to upload to Signal'}), 500
        # Update database with Signal URL
        uploaded_at = int(time.time())
        _ = db.update_custom_pack_signal_url(pack_name, signal_url, uploaded_at)
        return jsonify({
            'success': True,
            'signal_url': signal_url,
            'uploaded_at': uploaded_at
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        app.logger.error(f"Error uploading custom pack to Signal: {e}", exc_info=True)
        return jsonify({'error': f'Internal error: {str(e)}'}), 500

@app.route('/api/custom-packs/<pack_name>', methods=['DELETE'])
def delete_custom_pack(pack_name: str) -> tuple[Response, int] | Response:
    try:
        if not db.get_custom_pack(pack_name):
            return jsonify({'error': 'Pack not found'}), 404
        success: bool = db.delete_custom_pack(pack_name)
        if success:
            return jsonify({'success': True})
        return jsonify({'error': 'Failed to delete pack'}), 500
    except Exception as e:
        app.logger.error(f"Error deleting custom pack: {e}", exc_info=True)
        return jsonify({'error': f'Internal error: {str(e)}'}), 500

# Export endpoints
@app.route('/api/export/pack/<pack_name>', methods=['GET'])
def export_pack(pack_name: str) -> tuple[Response, int] | Response:
    if not db.get_sticker_pack(pack_name):
        return jsonify({'error': 'Pack not found'}), 404
    json_data: str = db.export_single_pack_to_json(pack_name)
    response: Response = make_response(json_data)
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = f'attachment; filename={pack_name}.json'
    return response

@app.route('/api/export/packs', methods=['GET'])
def export_all_packs() -> Response:
    pack_names: list[str] = db.get_all_pack_names()
    if not pack_names:
        return jsonify({'error': 'No packs to export'}), 404
    # Create ZIP file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for pack_name in pack_names:
            json_data: str = db.export_single_pack_to_json(pack_name)
            zip_file.writestr(f'{pack_name}.json', json_data)
    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name='sticker_packs.zip'
    )

@app.route('/api/export/custom-pack/<pack_name>', methods=['GET'])
def export_custom_pack(pack_name: str) -> tuple[Response, int] | Response:
    if not db.get_custom_pack(pack_name):
        return jsonify({'error': 'Custom pack not found'}), 404
    json_data: str = db.export_single_custom_pack_to_json(pack_name)
    response: Response = make_response(json_data)
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = f'attachment; filename={pack_name}_custom.json'
    return response

@app.route('/api/export/custom-packs', methods=['GET'])
def export_all_custom_packs() -> Response:
    pack_names: list[str] = db.get_all_custom_pack_names()
    if not pack_names:
        return jsonify({'error': 'No custom packs to export'}), 404
    # Create ZIP file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for pack_name in pack_names:
            json_data: str = db.export_single_custom_pack_to_json(pack_name)
            zip_file.writestr(f'{pack_name}_custom.json', json_data)
    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name='custom_packs.zip'
    )

@app.route('/sticker_files/<pack_name>/<filename>')
def serve_sticker(pack_name: str, filename: str) -> Response:
    pack_dir: Path = DOWNLOAD_DIR / pack_name
    return send_from_directory(pack_dir, filename)

def main() -> None:
    app.run(debug=False, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()
