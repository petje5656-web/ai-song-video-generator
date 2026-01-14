import re
import os
from pathlib import Path
from typing import Optional, Dict
from lyricflow.core.lyrics_provider import create_fetcher
from groq import Groq


class LyricsModule:
    def __init__(self, groq_api_key: str):
        self.fetcher = create_fetcher("lrclib")
        self.client = Groq(api_key=groq_api_key)
    
    def fetch_raw(self, title: str, artist: str) -> Optional[Dict]:
        """Fetch lyrics from LRCLIB"""
        try:
            return self.fetcher.fetch(title, artist)
        except Exception as e:
            print(f"Fetch error: {e}")
            return None
    
    def clean_lyrics(self, synced_lyrics: str) -> str:
        """Remove timestamps from LRC format"""
        lines = synced_lyrics.split('\n')
        clean = []
        
        for line in lines:
            if line.startswith('[') and ']' in line:
                if any(tag in line.lower() for tag in ['ti:', 'ar:', 'al:', 'length:', 'by:']):
                    continue
                match = re.search(r'\[[\d:.]+\](.*)', line)
                if match:
                    text = match.group(1).strip()
                    if text:
                        clean.append(text)
            elif line.strip():
                clean.append(line.strip())
        
        return '\n'.join(clean)
    
    def add_structure(self, lyrics: str, title: str, artist: str) -> str:
        """Add AI music generation tags"""
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
            return f"[verse]\n{lyrics}\n ; \n[outro-medium]"
    
    def save_lrc(self, result: Dict, filepath: str):
        """Save LRC file"""
        self.fetcher.save_lrc(result, Path(filepath))
    
    def get_lyrics(self, title: str, artist: str, structured: bool = True) -> Optional[Dict[str, str]]:
        """
        Get lyrics in multiple formats
        
        Returns:
            Dict with 'raw', 'synced', 'clean', 'structured' lyrics
        """
        print(f"🔍 Fetching '{title}' by {artist}...")
        
        result = self.fetch_raw(title, artist)
        if not result or not result.get('synced_lyrics'):
            print("❌ No lyrics found")
            return None
        
        print("🧹 Cleaning timestamps...")
        clean = self.clean_lyrics(result['synced_lyrics'])
        
        output = {
            'raw': result,
            'synced': result['synced_lyrics'],
            'clean': clean,
            'structured': None
        }
        
        if structured:
            print("🤖 Adding structure tags...")
            output['structured'] = self.add_structure(clean, title, artist)
        
        return output


if __name__ == "__main__":
    
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY not set")
        exit(1)
    
    module = LyricsModule(groq_api_key=GROQ_API_KEY)
    
    title = "Hey Jude"
    artist = "The Beatles"
    
    lyrics = module.get_lyrics(title=title, artist=artist, structured=True)
    
    if lyrics:
        with open('structured_lyrics.txt', 'w') as f:
            f.write(lyrics['structured'])
        
        print("\n" + "="*60)
        print("📝 STRUCTURED LYRICS (first 600 chars)")
        print("="*60)
        print(lyrics['structured'][:600])
        print("="*60)
        print("\n✅ Saved to structured_lyrics.txt")
        print("✅ Ready! Run generate_song.py next.")
    else:
        print("❌ Failed to fetch lyrics")
