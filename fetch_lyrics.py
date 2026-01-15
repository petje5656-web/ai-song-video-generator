import re
import os
import json
import sys
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from collections import Counter
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
    
    def fetch_raw_from_lrclib(self, title: str, artist: str) -> Optional[Dict]:
        """Fetch lyrics from LRClib API using requests"""
        import requests
        try:
            url = "https://lrclib.net/api/search"
            params = {
                "track_name": title,
                "artist_name": artist
            }
            response = requests.get(url, params=params)
            if response.status_code == 200:
                results = response.json()
                if results:
                    return {
                        'plain_lyrics': results[0].get('plainLyrics', ''),
                        'synced_lyrics': results[0].get('syncedLyrics', ''),
                        'provider': 'lrclib'
                    }
        except Exception as e:
            print(f"LRClib error: {e}")
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
    
    def detect_chorus_regex(self, lyrics: str, min_lines: int = 2, max_lines: int = 6) -> List[Tuple[str, int]]:
        """Detect chorus by finding repeating line sequences"""
        lines = [l.strip() for l in lyrics.split('\n') if l.strip() and not l.strip().startswith('[')]
        
        if len(lines) < min_lines:
            return []
        
        sequences = []
        
        for seq_len in range(max_lines, min_lines - 1, -1):
            for i in range(len(lines) - seq_len + 1):
                sequence = tuple(lines[i:i + seq_len])
                sequence_text = '\n'.join(sequence)
                
                count = 0
                for j in range(len(lines) - seq_len + 1):
                    check_seq = tuple(lines[j:j + seq_len])
                    if sequence == check_seq:
                        count += 1
                
                if count >= 2:
                    sequences.append((sequence_text, count))
        
        if not sequences:
            return []
        
        sequences.sort(key=lambda x: (x[1], len(x[0])), reverse=True)
        
        seen = set()
        unique_sequences = []
        for seq_text, count in sequences:
            seq_lines = tuple(seq_text.split('\n'))
            if seq_lines not in seen:
                seen.add(seq_lines)
                unique_sequences.append((seq_text, count))
        
        return unique_sequences[:3]
    
    def add_structure(self, lyrics: str, title: str, artist: str, retry_count=0) -> str:
        choruses = self.detect_chorus_regex(lyrics)
        
        chorus_hint = ""
        if choruses:
            print(f"🎵 Detected {len(choruses)} potential chorus(es)")
            for i, (chorus_text, count) in enumerate(choruses, 1):
                print(f"   Chorus {i} (appears {count}x): {chorus_text[:50]}...")
            
            chorus_hint = f"\n\nDETECTED CHORUSES (use these for [chorus] sections):\n"
            for i, (chorus_text, count) in enumerate(choruses, 1):
                chorus_hint += f"\nChorus {i} (repeats {count}x):\n{chorus_text}\n"

        prompt = f"""Format these lyrics for AI choir music generation. CRITICAL RULES:

CHOIR THEME: Emphasize group vocals, harmonies, and powerful collective singing

STRUCTURE RULES:
1. MUST START WITH: [verse] or [chorus] (NEVER [intro])
2. ALLOWED TAGS: [verse], [chorus], [bridge], [inst-medium], [inst-long], [outro-short]
3. NO [inst-short] allowed - only medium and long instrumentals
4. ALWAYS end with [outro-short] (never medium or long outro)

VERSE SPLITTING RULE:
- IF a verse has MORE than 12 lines:
  * Split at line 12
  * Add " ; " on new line
  * Add [inst-medium]
  * Continue rest as [bridge]
  * Add " ; " on new line
  * Add [inst-medium] after bridge

FORMATTING:
1. Lyrics on separate lines AFTER the tag
2. To add instrumental: end section with " ; " on new line, then instrumental tag
3. NO numbers in tags
4. Repeat [verse]/[chorus] for multiple sections{chorus_hint}

Song: "{title}" by {artist}

Lyrics:
{lyrics}

Output ONLY formatted lyrics. Remember: [outro-short] at the end, NO [inst-short]."""

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
            formatted = re.sub(r'\[inst-short\]', '[inst-medium]', formatted, flags=re.IGNORECASE)
            formatted = re.sub(r'\[outro-(medium|long)\]', '[outro-short]', formatted, flags=re.IGNORECASE)
            
            if not re.search(r'\[outro-short\]', formatted, re.IGNORECASE):
                formatted += '\n ; \n[outro-short]'
            
            formatted = re.sub(r'\n{3,}', '\n\n', formatted)
            
            return formatted.strip()
        except Exception as e:
            print(f"AI error: {e}")
            
            if retry_count < len(self.api_keys) - 1:
                self._rotate_key()
                return self.add_structure(lyrics, title, artist, retry_count + 1)
            
            return f"[verse]\n{lyrics}\n ; \n[outro-short]"
    
    def get_lyrics(self, title: str, artist: str, youtube_url: str = None, structured: bool = True) -> Optional[Dict[str, str]]:
        print(f"🔍 Fetching '{title}' by {artist}...")
        
        result = self.fetch_raw_from_lrclib(title, artist)
        if not result:
            print("❌ No lyrics found")
            return None
        
        lyrics_text = result.get('plain_lyrics') or result.get('synced_lyrics') or ""
        
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
            'provider': result.get('provider', 'lrclib')
        }
        
        if structured:
            print("🎶 Detecting chorus patterns...")
            choruses = self.detect_chorus_regex(clean)
            output['detected_choruses'] = choruses
            
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
    elif os.path.exists('album_progress.json'):
        with open('album_progress.json', 'r') as f:
            progress = json.load(f)
        
        current_track = progress['current_track']
        title = current_track['title']
        artist = progress['artist']
        youtube_url = current_track.get('youtube_url')
    else:
        title = os.getenv('SONG_TITLE', 'Hey Jude')
        artist = os.getenv('SONG_ARTIST', 'The Beatles')
        youtube_url = None
        print(f"ℹ️  Using defaults: '{title}' by {artist}")
    
    lyrics = module.get_lyrics(title=title, artist=artist, youtube_url=youtube_url, structured=True)
    
    if lyrics:
        with open('structured_lyrics.txt', 'w') as f:
            f.write(lyrics['structured'])
        
        metadata = {
            'title': title,
            'artist': artist,
            'youtube_url': youtube_url,
            'provider': lyrics['provider'],
            'detected_choruses': lyrics.get('detected_choruses', [])
        }
        with open('lyrics_metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print("\n" + "="*60)
        print(f"📝 Provider: {lyrics['provider']}")
        if lyrics.get('detected_choruses'):
            print(f"🎵 Choruses detected: {len(lyrics['detected_choruses'])}")
        print("="*60)
        print(lyrics['structured'][:600])
        print("="*60)
        print("\n✅ Saved to structured_lyrics.txt")
        print("✅ Structure rules applied:")
        print("   - Only [inst-medium] and [inst-long] allowed")
        print("   - Always ends with [outro-short]")
        print("   - Long verses (>12 lines) split with bridge")
    else:
        print("❌ Failed to fetch lyrics")
        sys.exit(1)