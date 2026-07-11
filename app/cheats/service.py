import hashlib
import os
import re
import threading
import time

import requests


_TITLE_ID_RE = re.compile(r'^[0-9A-F]{16}$')
_BUILD_ID_RE = re.compile(r'^[0-9A-F]{16}$')
_MAX_PROVIDER_RESPONSE = 8 * 1024 * 1024
_MAX_CHEAT_CONTENT = 1024 * 1024


class InvalidCheatIdentifier(ValueError):
    pass


class CheatService:
    """Fetch and normalize Atmosphere cheats without exposing providers to clients."""

    def __init__(self, session=None, cache_ttl_s=None):
        self._session = session or requests.Session()
        self._cache_ttl_s = int(cache_ttl_s or os.getenv('AEROFOIL_CHEATS_CACHE_TTL_S', '900'))
        base = os.getenv(
            'AEROFOIL_CHEATS_DB_BASE_URL',
            'https://raw.githubusercontent.com/HamletDuFromage/switch-cheats-db/master',
        ).rstrip('/')
        self._providers = (
            ('community', f'{base}/cheats_gbatemp/{{title_id}}.json'),
            ('database', f'{base}/cheats/{{title_id}}.json'),
            ('graphics', f'{base}/cheats_gfx/{{title_id}}.json'),
        )
        self._cache = {}
        self._lock = threading.Lock()

    @staticmethod
    def normalize_title_id(value):
        normalized = str(value or '').strip().upper()
        if not _TITLE_ID_RE.fullmatch(normalized):
            raise InvalidCheatIdentifier('Title ID must contain exactly 16 hexadecimal characters.')
        return normalized

    @staticmethod
    def normalize_build_id(value):
        normalized = str(value or '').strip().upper()
        if not _BUILD_ID_RE.fullmatch(normalized):
            raise InvalidCheatIdentifier('Build ID must contain exactly 16 hexadecimal characters.')
        return normalized

    def _get_json(self, url):
        response = self._session.get(
            url,
            headers={'Accept': 'application/json', 'User-Agent': 'AeroFoil/cheats'},
            timeout=(5, 20),
            stream=True,
        )
        if response.status_code == 404:
            return {}
        response.raise_for_status()
        raw = bytearray()
        for chunk in response.iter_content(64 * 1024):
            raw.extend(chunk)
            if len(raw) > _MAX_PROVIDER_RESPONSE:
                raise ValueError('Cheat provider response exceeds the size limit.')
        return response.json() if not raw else __import__('json').loads(raw.decode('utf-8'))

    def _load_title(self, title_id):
        now = time.monotonic()
        with self._lock:
            cached = self._cache.get(title_id)
            if cached and now - cached[0] < self._cache_ttl_s:
                return cached[1]

        merged = {}
        errors = []
        for source, template in self._providers:
            try:
                payload = self._get_json(template.format(title_id=title_id))
            except Exception as exc:
                errors.append(f'{source}: {exc}')
                continue
            if not isinstance(payload, dict):
                continue
            for raw_build_id, entries in payload.items():
                try:
                    build_id = self.normalize_build_id(raw_build_id)
                except InvalidCheatIdentifier:
                    continue
                if not isinstance(entries, dict):
                    continue
                bucket = merged.setdefault(build_id, [])
                known_hashes = {item['content_hash'] for item in bucket}
                for name, content in entries.items():
                    if not isinstance(name, str) or not isinstance(content, str):
                        continue
                    content = content.replace('\x00', '').strip()
                    if not content or len(content.encode('utf-8')) > _MAX_CHEAT_CONTENT:
                        continue
                    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                    if content_hash in known_hashes:
                        continue
                    bucket.append({
                        'id': content_hash,
                        'name': name.strip() or 'Unnamed cheat',
                        'content': content,
                        'content_hash': content_hash,
                        'source': source,
                    })
                    known_hashes.add(content_hash)

        result = {'builds': merged, 'provider_errors': errors}
        with self._lock:
            self._cache[title_id] = (now, result)
        return result

    def find_build(self, title_id, build_id):
        title_id = self.normalize_title_id(title_id)
        build_id = self.normalize_build_id(build_id)
        title = self._load_title(title_id)
        return {
            'title_id': title_id,
            'build_id': build_id,
            'match': 'exact' if build_id in title['builds'] else 'none',
            'cheats': list(title['builds'].get(build_id, [])),
            'available_build_ids': sorted(title['builds']),
            'provider_errors': list(title['provider_errors']),
        }

    def render(self, title_id, build_id, selected_ids):
        result = self.find_build(title_id, build_id)
        selected = set(selected_ids or [])
        entries = [item for item in result['cheats'] if item['id'] in selected]
        if not entries:
            raise ValueError('No valid cheats were selected for this build.')
        content = '\n\n'.join(item['content'].strip() for item in entries).strip() + '\n'
        return {
            'title_id': result['title_id'],
            'build_id': result['build_id'],
            'content': content,
            'sha256': hashlib.sha256(content.encode('utf-8')).hexdigest(),
            'selected': [{'id': item['id'], 'name': item['name'], 'source': item['source']} for item in entries],
        }
