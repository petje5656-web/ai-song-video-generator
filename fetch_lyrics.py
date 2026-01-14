import re
import subprocess
from pathlib import Path
from typing import Optional
from groq import Groq

class LyricFlowProcessor:
    
    def __init__(self, groq_api_key: str):
        self.client = Groq(api_key=groq_api_key)
        
    def fetch_lyrics(self, title: str, artist: str, output_file: str = "lyrics.txt") -> bool:
        try:
            cmd = ["lyricflow", "fetch", "-t", title, "-a", artist, "--output", output_file]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return Path(output_file).exists()
        except subprocess.CalledProcessError as e:
            print(f"Error fetching lyrics: {e.stderr}")
            return False
    
    def remove_timestamps(self, lrc_content: str) -> str:
        lines = lrc_content.split('\n')
        clean_lines = []
        
        for line in lines:
            if line.startswith('[') and ']' in line:
                if any(tag in line.lower() for tag in ['ti:', 'ar:', 'al:', 'length:', 'by:']):
                    continue
                
                match = re.search(r'\[[\d:.]+\](.*)', line)
                if match:
                    text = match.group(1).strip()
                    if text:
                        clean_lines.append(text)
            elif line.strip():
                clean_lines.append(line.strip())
        
        return '\n'.join(clean_lines)
    
    def add_structure_tags(self, lyrics: str, title: str, artist: str) -> str:
        
        prompt = f"""Analyze these lyrics and format them for AI music generation. Follow these EXACT rules:

ALLOWED TAGS:
- [verse] - Story/narrative sections (must contain lyrics)
- [chorus] - Main hook/repeated section (must contain lyrics)
- [bridge] - Musical departure (must contain lyrics)
- [inst-short] - Short instrumental break (NO lyrics, 0-10 seconds)
- [inst-medium] - Medium instrumental break (NO lyrics, 10-20 seconds)
- [outro] - Ending section (can have lyrics or be instrumental)

CRITICAL FORMATTING RULES:
1. Use " ; " (space-semicolon-space) BEFORE instrumental tags when they follow lyrical sections
2. Write lyrics on separate lines within each section
3. NO numbers in tags (use [verse], NOT [verse 1])
4. Repeat tags for multiple verses/choruses
5. NO intro tags - start directly with [verse] or [chorus]

STRUCTURE GUIDE:
- Start with [verse] or [chorus]
- Use [bridge] once for musical variation
- Add " ; " before [inst-short] or [inst-medium] when they follow lyrics
- End with [outro]

Song: "{title}" by {artist}

Lyrics:
{lyrics}

Example format:
[verse]
First line here
Second line here
 ; 
[inst-short]
[chorus]
Chorus line one
Chorus line two
 ; 
[inst-medium]
[bridge]
Bridge lyrics here
 ; 
[outro]

Output ONLY the formatted lyrics, no explanations."""

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=4000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error with Groq API: {e}")
            return lyrics
    
    def process_lyrics_file(self, input_file: str, output_file: str, 
                           title: str, artist: str) -> str:
        
        with open(input_file, 'r', encoding='utf-8') as f:
            lrc_content = f.read()
        
        clean_lyrics = self.remove_timestamps(lrc_content)
        structured_lyrics = self.add_structure_tags(clean_lyrics, title, artist)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(structured_lyrics)
        
        return structured_lyrics
    
    def fetch_and_process(self, title: str, artist: str, 
                         output_file: str = "structured_lyrics.txt") -> Optional[str]:
        
        temp_file = "temp_lyrics.lrc"
        
        print(f"🔍 Fetching lyrics for '{title}' by {artist}...")
        if not self.fetch_lyrics(title, artist, temp_file):
            return None
        
        print("🧹 Cleaning timestamps...")
        print("🤖 Adding structure tags with AI...")
        
        structured = self.process_lyrics_file(temp_file, output_file, title, artist)
        
        Path(temp_file).unlink(missing_ok=True)
        
        print(f"✅ Saved to {output_file}")
        return structured
    
    def get_lyrics_snippet(self, lyrics: str, max_chars: int = 400) -> str:
        if len(lyrics) <= max_chars:
            return lyrics
        snippet = lyrics[:max_chars]
        last_newline = snippet.rfind('\n')
        if last_newline > 0:
            snippet = snippet[:last_newline]
        return snippet + "\n\n... (truncated)"


if __name__ == "__main__":
    GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
    
    title = "Hey Jude"
    artist = "The Beatles"
    
    processor = LyricFlowProcessor(groq_api_key=GROQ_API_KEY)
    
    structured_lyrics = processor.fetch_and_process(
        title=title,
        artist=artist,
        output_file="structured_lyrics.txt"
    )
    
    if structured_lyrics:
        snippet = processor.get_lyrics_snippet(structured_lyrics, max_chars=400)
        print("\n" + "="*60)
        print("📝 LYRICS PREVIEW")
        print("="*60)
        print(f"🎤 Song: {title}")
        print(f"🎸 Artist: {artist}")
        print("="*60)
        print(snippet)
        print("="*60)
        print("\n✅ Ready! Run generate_song.py next.")
    else:
        print("❌ Failed to fetch lyrics")