from pathlib import Path

from flask import Flask, Response, jsonify, make_response, render_template, request, send_from_directory
from rapidfuzz import fuzz

from src.config import DATABASE_FILE, DOWNLOAD_DIR
from src.database import CustomPackSticker, Database, StickerPackRecord, StickerSearchResult

app: Flask = Flask(__name__)
db: Database = Database(DATABASE_FILE)

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
        return stickers[:100]
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
    return [r[0] for r in results[:200]]

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
    packs: list[StickerPackRecord] = db.search_sticker_packs(query)
    filtered_packs: list[StickerPackRecord] = fuzzy_search_packs(query, packs)
    return jsonify([dict(pack) for pack in filtered_packs])

@app.route('/api/packs/<pack_name>')
def get_pack(pack_name: str) -> tuple[Response, int] | Response:
    pack_info = db.get_sticker_pack(pack_name)
    if not pack_info:
        return jsonify({'error': 'Pack not found'}), 404
    stickers = db.get_pack_stickers(pack_name)
    response_pack: dict[str, str | int | list[dict[str, str | None]]] = {
        'name': pack_info['name'],
        'title': pack_info['title'],
        'artist': pack_info['artist'],
        'last_update': pack_info['last_update'],
        'sticker_count': pack_info['sticker_count'],
        'stickers': [dict(s) for s in stickers]
    }

    return jsonify(response_pack)


@app.route('/api/packs/<pack_name>/artist', methods=['POST'])
def update_pack_artist(pack_name: str) -> tuple[Response, int] | Response:
    if not db.get_sticker_pack(pack_name):
        return jsonify({'error': 'Pack not found'}), 404
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400
    artist: str = data.get('artist', 'Unknown')
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

@app.route('/api/stickers/search')
def search_stickers() -> Response:
    query: str = request.args.get('q', '')
    stickers: list[StickerSearchResult] = db.search_stickers(query)
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
    return jsonify(results)

@app.route('/api/custom-packs', methods=['GET'])
def get_custom_packs() -> Response:
    packs_with_counts: list[tuple[dict[str, str], int]] = db.get_all_custom_packs()
    result: dict[str, dict[str, str | list[CustomPackSticker]]] = {
        pack['name']: {
            'name': pack['name'],
            'title': pack['title'],
            'stickers': db.get_custom_pack_stickers(pack['name'])
        }
        for pack, _ in packs_with_counts
    }
    return jsonify(result)

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
    stickers: list[CustomPackSticker] = db.get_custom_pack_stickers(pack_name)
    return jsonify({
        'name': pack['name'],
        'title': pack['title'],
        'stickers': [dict(s) for s in stickers]
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
                emoji=s.get('emoji', '')
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
@app.route('/api/export/packs', methods=['GET'])
def export_packs() -> Response:
    json_data: str = db.export_sticker_packs_to_json()
    response: Response = make_response(json_data)
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = 'attachment; filename=sticker_packs.json'
    return response

@app.route('/api/export/pack/<pack_name>', methods=['GET'])
def export_pack(pack_name: str) -> tuple[Response, int] | Response:
    if not db.get_sticker_pack(pack_name):
        return jsonify({'error': 'Pack not found'}), 404
    json_data: str = db.export_stickers_to_json(pack_name)
    response: Response = make_response(json_data)
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = f'attachment; filename={pack_name}_stickers.json'
    return response

@app.route('/api/export/custom-packs', methods=['GET'])
def export_custom_packs() -> Response:
    json_data: str = db.export_custom_packs_to_json()
    response: Response = make_response(json_data)
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = 'attachment; filename=custom_packs.json'
    return response

@app.route('/sticker_files/<pack_name>/<filename>')
def serve_sticker(pack_name: str, filename: str) -> Response:
    pack_dir: Path = DOWNLOAD_DIR / pack_name
    return send_from_directory(pack_dir, filename)

def main() -> None:
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()
