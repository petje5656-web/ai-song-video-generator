import re
import os
import json
import sys
from pathlib import Path
from typing import Optional, Dict
from lyricflow.core.lrclib_with_fallback import fetch_with_fallback
from groq import Groq

class LyricsModule:
    def __init__(self, api_keys: list):
        self.api_keys = api_keys
        self.current_key_index = 0
        self.client = self._get_client()
    
    def _get_client(self):
        return Groq(api_key=self.api_keys[self.current_key_index])
    
    def _rotate_key(self):
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self.client = self._get_client()
        print(f"🔄 Rotated to API key {self.current_key_index + 1}/{len(self.api_keys)}")
    
    def fetch_raw(self, title: str, artist: str, youtube_url: str = None) -> Optional[Dict]:
        try:
            result = fetch_with_fallback(
                title=title,
                artist=artist,
                audio_url=youtube_url,
                strict_matching=True,
                use_whisper=True if youtube_url else False
            )
            return result
        except Exception as e:
            print(f"Fetch error: {e}")
            return None
    
    def clean_lyrics(self, lyrics_text: str) -> str:
        if not lyrics_text:
            return ""
        
        lines = lyrics_text.split('\n')
        clean = []
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            if line.startswith('[') and ']' in line:
                if any(tag in line.lower() for tag in ['ti:', 'ar:', 'al:', 'length:', 'by:', 'offset:']):
                    continue
                
                match = re.search(r'\[[\d:.]+\](.*)', line)
                if match:
                    text = match.group(1).strip()
                    if text:
                        clean.append(text)
                else:
                    text = re.sub(r'\[.*?\]', '', line).strip()
                    if text:
                        clean.append(text)
            else:
                clean.append(line)
        
        result = '\n'.join(clean)
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result.strip()
    
    def add_structure(self, lyrics: str, title: str, artist: str, retry_count=0) -> str:
        prompt = f"""Format these lyrics for AI music generation. CRITICAL RULES:

MUST START WITH: [verse] or [chorus] (NEVER [intro])
ALLOWED STRUCTURE TAGS: [verse], [chorus], [bridge], [outro-short], [outro-medium], [outro-long]
ALLOWED INSTRUMENTAL TAGS: [inst-short], [inst-medium], [inst-long]

FORMATTING RULES:
1. First line MUST be [verse] or [chorus]
2. Lyrics on separate lines AFTER the tag
3. To add instrumental: end section with " ; " on new line, then instrumental tag
4. NO numbers in tags
5. Repeat [verse]/[chorus] for multiple sections
6. End with [outro-short/medium/long]

Song: "{title}" by {artist}

Lyrics:
{lyrics}

Output ONLY formatted lyrics."""

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=4000
            )
            
            formatted = response.choices[0].message.content.strip()
            
            if not formatted.split('\n')[0].strip().startswith('['):
                formatted = '[verse]\n' + formatted
            
            formatted = re.sub(r'\[intro[-\w]*\]', '', formatted, flags=re.IGNORECASE)
            formatted = re.sub(r'\n{3,}', '\n\n', formatted)
            
            return formatted.strip()
        except Exception as e:
            print(f"AI error: {e}")
            
            if retry_count < len(self.api_keys) - 1:
                self._rotate_key()
                return self.add_structure(lyrics, title, artist, retry_count + 1)
            
            return f"[verse]\n{lyrics}\n ; \n[outro-medium]"
    
    def get_lyrics(self, title: str, artist: str, youtube_url: str = None, structured: bool = True) -> Optional[Dict[str, str]]:
        print(f"🔍 Fetching '{title}' by {artist}...")
        
        result = self.fetch_raw(title, artist, youtube_url)
        if not result:
            print("❌ No lyrics found")
            return None
        
        lyrics_text = result.get('synced_lyrics') or result.get('plain_lyrics') or ""
        
        if not lyrics_text:
            print("❌ No lyrics text available")
            return None
        
        print("🧹 Cleaning lyrics...")
        clean = self.clean_lyrics(lyrics_text)
        
        output = {
            'raw': result,
            'synced': result.get('synced_lyrics'),
            'plain': result.get('plain_lyrics'),
            'clean': clean,
            'structured': None,
            'provider': result.get('provider', 'unknown')
        }
        
        if structured:
            print("🤖 Adding structure tags...")
            output['structured'] = self.add_structure(clean, title, artist)
        
        return output

if __name__ == "__main__":
    api_keys_str = os.getenv("GROQ_API_KEYS", "")
    api_keys = [k.strip() for k in api_keys_str.split(',') if k.strip()]
    
    if not api_keys:
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            api_keys = [api_key]
        else:
            print("❌ GROQ_API_KEYS or GROQ_API_KEY not set")
            sys.exit(1)
    
    print(f"✓ Loaded {len(api_keys)} API key(s)")
    
    module = LyricsModule(api_keys=api_keys)
    
    if len(sys.argv) >= 3:
        title = sys.argv[1]
        artist = sys.argv[2]
        youtube_url = sys.argv[3] if len(sys.argv) > 3 else None
    else:
        with open('album_progress.json', 'r') as f:
            progress = json.load(f)
        
        current_track = progress['current_track']
        title = current_track['title']
        artist = progress['artist']
        youtube_url = current_track.get('youtube_url')
    
    lyrics = module.get_lyrics(title=title, artist=artist, youtube_url=youtube_url, structured=True)
    
    if lyrics:
        with open('structured_lyrics.txt', 'w') as f:
            f.write(lyrics['structured'])
        
        print("\n" + "="*60)
        print(f"📝 Provider: {lyrics['provider']}")
        print("="*60)
        print(lyrics['structured'][:600])
        print("="*60)
        print("\n✅ Saved to structured_lyrics.txt")
    else:
        print("❌ Failed to fetch lyrics")
        sys.exit(1)