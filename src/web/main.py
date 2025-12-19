import json
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, send_from_directory
from rapidfuzz import fuzz

from src.config import REGISTRY_FILE, CUSTOM_PACKS_FILE, DOWNLOAD_DIR

app: Flask = Flask(__name__)

PackRegistry = dict[str, dict[str, str | int | dict[str, dict[str, str | int | bool | None]]]]
StickerResult = dict[str, str | dict[str, str | int | bool | None]]

def load_registry() -> PackRegistry:
    if REGISTRY_FILE.exists():
        with open(REGISTRY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_registry(registry: PackRegistry) -> None:
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_FILE, 'w', encoding='utf-8') as f:
        json.dump(registry, f, ensure_ascii=False)

def load_custom_packs() -> dict:
    if CUSTOM_PACKS_FILE.exists():
        with open(CUSTOM_PACKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_custom_packs(custom_packs: dict) -> None:
    CUSTOM_PACKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CUSTOM_PACKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(custom_packs, f, ensure_ascii=False)

def fuzzy_search_packs(query: str, registry: PackRegistry, limit: int | None = None) -> list[dict[str, str | int | dict[str, dict[str, str | int | bool | None]]]]:
    if not query:
        return [pack for pack in registry.values()][:limit] if limit else [pack for pack in registry.values()]
    results: list[tuple[dict[str, str | int | dict[str, dict[str, str | int | bool | None]]], float]] = []
    for pack_name, pack_info in registry.items():
        # Search in pack name and title
        title = pack_info.get('title', '')
        title_str = title if isinstance(title, str) else ''
        name_score: float = max(
            fuzz.partial_ratio(query.lower(), pack_name.lower()),
            fuzz.partial_ratio(query.lower(), title_str.lower())
        )
        # Search in artist
        artist = pack_info.get('artist', '')
        artist_str = artist if isinstance(artist, str) else ''
        artist_score: float = fuzz.partial_ratio(query.lower(), artist_str.lower())
        # Take the best score
        score: float = max(name_score, artist_score)
        if score > 40:
            results.append((pack_info, score))
    # Sort by score
    results.sort(key=lambda x: x[1], reverse=True)
    return [r[0] for r in results[:limit]] if limit else [r[0] for r in results]

def load_emoji_map(pack_name: str) -> dict[str, str]:
    pack_dir: Path = DOWNLOAD_DIR / pack_name
    emoji_file: Path = pack_dir / "emojis.json"
    if emoji_file.exists():
        try:
            with open(emoji_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def fuzzy_search_stickers(query: str, registry: PackRegistry, limit: int | None = None) -> list[StickerResult]:
    if not query:
        # Return recent stickers if no query
        all_stickers: list[StickerResult] = []
        for pack_name, pack_info in registry.items():
            stickers = pack_info.get('stickers', {})
            if not isinstance(stickers, dict):
                continue
            emoji_map: dict[str, str] = load_emoji_map(pack_name)
            title = pack_info.get('title', '')
            title_str: str = title if isinstance(title, str) else ''
            artist: str = pack_info.get('artist', 'Unknown')
            artist_str: str = artist if isinstance(artist, str) else 'Unknown'
            for unique_id, sticker_data in list(stickers.items())[:10]:
                emoji: str = emoji_map.get(unique_id, '')
                if not isinstance(sticker_data, dict):
                    continue
                all_stickers.append({
                    'pack_name': pack_name,
                    'pack_title': title_str,
                    'artist': artist_str,
                    'sticker': sticker_data,
                    'emoji': emoji
                })
        return all_stickers[:limit] if limit else all_stickers
    results: list[tuple[StickerResult, float]] = []
    for pack_name, pack_info in registry.items():
        stickers = pack_info.get('stickers', {})
        if not isinstance(stickers, dict):
            continue
        emoji_map: dict[str, str] = load_emoji_map(pack_name)
        title = pack_info.get('title', '')
        pack_title: str = title if isinstance(title, str) else ''
        artist: str = pack_info.get('artist', 'Unknown')
        artist_str: str = artist if artist else 'Unknown'
        for unique_id, sticker_data in stickers.items():
            if not sticker_data:
                continue
            emoji: str = emoji_map.get(unique_id, '')
            # Calculate scores for different fields
            pack_score: float = max(
                fuzz.partial_ratio(query.lower(), pack_name.lower()),
                fuzz.partial_ratio(query.lower(), pack_title.lower())
            )
            artist_score: float = fuzz.partial_ratio(query.lower(), artist_str.lower())
            emoji_score: float = (
                fuzz.partial_ratio(query.lower(), emoji.lower()) if emoji else 0
            )
            # Take the best score
            score: float = max(pack_score, artist_score, emoji_score)
            if score > 40:
                results.append(({
                    'pack_name': pack_name,
                    'pack_title': pack_title,
                    'artist': artist_str,
                    'sticker': sticker_data,
                    'emoji': emoji
                }, score))
    # Sort by score
    results.sort(key=lambda x: x[1], reverse=True)
    return [r[0] for r in results[:limit]] if limit else [r[0] for r in results]

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
    registry: PackRegistry = load_registry()
    results = fuzzy_search_packs(query, registry)
    return jsonify(results)

@app.route('/api/packs/<pack_name>')
def get_pack(pack_name: str) -> tuple[Response, int] | Response:
    registry: PackRegistry = load_registry()
    pack_info = registry.get(pack_name)
    if not pack_info:
        return jsonify({'error': 'Pack not found'}), 404
    # Load emoji mapping
    emoji_map: dict[str, str] = load_emoji_map(pack_name)
    # Enhance sticker data with emojis
    stickers = pack_info.get('stickers', {})
    if isinstance(stickers, dict):
        enhanced_stickers: list[dict[str, str | int | bool | None]] = []
        for unique_id, sticker_data in stickers.items():
            if sticker_data:
                enhanced: dict[str, str | int | bool | None] = dict(sticker_data)
                emoji = sticker_data.get('emoji', '')
                emoji_str = emoji if isinstance(emoji, str) else ''
                enhanced['emoji'] = emoji_map.get(unique_id, emoji_str)
                enhanced_stickers.append(enhanced)
        response_pack: dict[str, str | int | list[dict[str, str | int | bool | None]]] = {
            'name': pack_info.get('name', pack_name),
            'title': pack_info.get('title', ''),
            'artist': pack_info.get('artist', 'Unknown'),
            'last_update': pack_info.get('last_update', 0),
            'sticker_count': pack_info.get('sticker_count', 0),
            'stickers': enhanced_stickers
        }
        return jsonify(response_pack)
    return jsonify(pack_info)

@app.route('/api/packs/<pack_name>/artist', methods=['POST'])
def update_pack_artist(pack_name: str) -> tuple[Response, int] | Response:
    registry: PackRegistry = load_registry()
    if pack_name not in registry:
        return jsonify({'error': 'Pack not found'}), 404
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400
    artist: str = data.get('artist', 'Unknown')
    registry[pack_name]['artist'] = artist
    save_registry(registry)
    return jsonify({'success': True, 'artist': artist})

@app.route('/api/packs/<pack_name>/emoji', methods=['POST'])
def update_sticker_emoji(pack_name: str) -> tuple[Response, int] | Response:
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400
    unique_id: str = data.get('unique_id', '')
    emojis: str = data.get('emojis', '')
    if not unique_id:
        return jsonify({'error': 'unique_id required'}), 400
    emoji_map = load_emoji_map(pack_name)
    emoji_map[unique_id] = emojis
    save_emoji_map(pack_name, emoji_map)
    return jsonify({'success': True, 'unique_id': unique_id, 'emojis': emojis})


@app.route('/api/stickers/search')
def search_stickers() -> Response:
    query: str = request.args.get('q', '')
    registry: PackRegistry = load_registry()
    results = fuzzy_search_stickers(query, registry)
    return jsonify(results)

@app.route('/api/custom-packs', methods=['GET'])
def get_custom_packs() -> Response:
    custom_packs = load_custom_packs()
    return jsonify(custom_packs)

@app.route('/api/custom-packs', methods=['POST'])
def create_custom_pack() -> tuple[Response, int]:
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'Invalid request'}), 400
    custom_packs = load_custom_packs()
    pack_name = data['name']
    if pack_name in custom_packs:
        return jsonify({'error': 'Pack already exists'}), 400
    custom_packs[pack_name] = {
        'name': pack_name,
        'title': data.get('title', pack_name),
        'stickers': []
    }
    save_custom_packs(custom_packs)
    return jsonify({'success': True, 'pack': custom_packs[pack_name]}), 201

@app.route('/api/custom-packs/<pack_name>', methods=['GET'])
def get_custom_pack(pack_name: str) -> tuple[Response, int] | Response:
    custom_packs = load_custom_packs()
    if pack_name not in custom_packs:
        return jsonify({'error': 'Pack not found'}), 404
    return jsonify(custom_packs[pack_name])

@app.route('/api/custom-packs/<pack_name>', methods=['PUT'])
def update_custom_pack(pack_name: str) -> tuple[Response, int] | Response:
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400
    custom_packs = load_custom_packs()
    if pack_name not in custom_packs:
        return jsonify({'error': 'Pack not found'}), 404
    if 'title' in data:
        custom_packs[pack_name]['title'] = data['title']
    if 'stickers' in data:
        custom_packs[pack_name]['stickers'] = data['stickers']
    save_custom_packs(custom_packs)
    return jsonify({'success': True, 'pack': custom_packs[pack_name]})

@app.route('/api/custom-packs/<pack_name>', methods=['DELETE'])
def delete_custom_pack(pack_name: str) -> tuple[Response, int] | Response:
    custom_packs = load_custom_packs()
    if pack_name not in custom_packs:
        return jsonify({'error': 'Pack not found'}), 404
    del custom_packs[pack_name]
    save_custom_packs(custom_packs)
    return jsonify({'success': True})

@app.route('/sticker_files/<pack_name>/<filename>')
def serve_sticker(pack_name: str, filename: str) -> Response:
    pack_dir: Path = DOWNLOAD_DIR / pack_name
    return send_from_directory(pack_dir, filename)

def main() -> None:
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()
