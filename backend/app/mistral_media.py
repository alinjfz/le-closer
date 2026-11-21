"""Media requests through Mistral's API, independent of the installed SDK version."""
import base64
import json
from urllib.parse import urlparse, quote
import httpx

from . import config


def _headers():
    if not config.MISTRAL_API_KEY:
        raise ValueError('Set MISTRAL_API_KEY to enable speech and image generation.')
    return {'Authorization': f'Bearer {config.MISTRAL_API_KEY}'}


async def generate_speech(text: str) -> bytes:
    payload = {'model': config.TTS_MODEL, 'input': text, 'response_format': 'mp3'}
    if config.TTS_VOICE_ID:
        payload['voice_id'] = config.TTS_VOICE_ID
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post('https://api.mistral.ai/v1/audio/speech', headers=_headers(), json=payload)
        response.raise_for_status()
        return base64.b64decode(response.json()['audio_data'], validate=True)


async def generate_image(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post('https://api.mistral.ai/v1/conversations', headers=_headers(), json={
            'model': config.IMAGE_MODEL, 'inputs': prompt,
            'instructions': 'You must call the image_generation tool to create the requested image. Do not respond with a description instead of generating it.',
            'tools': [{'type': 'image_generation'}], 'store': False,
        })
        response.raise_for_status()
        for output in response.json().get('outputs', []):
            # Newer models return an image URL in the tool execution result.
            if output.get('type') == 'tool.execution' and output.get('name') == 'image_generation':
                info = output.get('info') or {}
                result = info.get('result', {}) if isinstance(info, dict) else {}
                if isinstance(result, str):
                    try:
                        result = json.loads(result)
                    except (ValueError, TypeError):
                        result = {}
                if isinstance(result, dict):
                    url = result.get('url')
                    if isinstance(url, str) and urlparse(url).scheme == 'https' and urlparse(url).hostname:
                        # Render the signed image URL directly; never send API credentials to it.
                        return url
            for chunk in output.get('content', []) if isinstance(output.get('content'), list) else []:
                if chunk.get('type') == 'tool_file' and chunk.get('tool') == 'image_generation':
                    file_id = quote(chunk['file_id'], safe='')
                    image = await client.get(f'https://api.mistral.ai/v1/files/{file_id}/content', headers=_headers())
                    image.raise_for_status()
                    data = image.content
                    mime = ('image/png' if data.startswith(b'\x89PNG\r\n\x1a\n') else
                            'image/jpeg' if data.startswith(b'\xff\xd8\xff') else
                            'image/webp' if data.startswith(b'RIFF') and data[8:12] == b'WEBP' else '')
                    if mime not in ('image/png', 'image/jpeg', 'image/webp'):
                        raise ValueError('Mistral returned an unsupported image format.')
                    return f'data:{mime};base64,' + base64.b64encode(image.content).decode()
    raise ValueError('The model returned no image. Retry with another description or check that IMAGE_MODEL supports image_generation.')
