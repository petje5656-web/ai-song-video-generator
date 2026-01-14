# AI Song Music Video Generator

Automatically generate music videos from song lyrics with AI-generated audio and animated GIFs.

## Features

- Fetch lyrics from any song using LyricFlow
- AI-powered lyric structuring with Groq
- Generate lofi/pop music with Gradio AI
- Create vertical music videos with GIF animations
- Adjustable playback speed (default: 0.8x for lofi effect)

## Setup

### Prerequisites

- Python 3.8+
- Google Colab (recommended) or local environment
- Groq API key
- GIF collection in `data/giphy.zip`

### Installation

```bash
pip install gradio_client groq lyricflow moviepy soundfile pydub
```

### Configuration

Update the following in the scripts:

```python
GROQ_API_KEY = "your_groq_api_key"
ZIP_PATH = 'data/giphy.zip'  # Path to your GIF collection
```

## Usage

### Run in 3 Cells

**Cell 1**: Fetch and process lyrics
```bash
python fetch_lyrics.py
```

**Cell 2**: Generate AI song at 0.8x speed
```bash
python generate_song.py
```

**Cell 3**: Create music video with GIFs
```bash
python create_video.py
```

### Configure Song

Edit these variables in `fetch_lyrics.py` and `generate_song.py`:

```python
title = "Your Song Title"
artist = "Artist Name"
```

## Lyric Format

The AI structures lyrics with these tags:

- `[verse]` - Story/narrative sections
- `[chorus]` - Main hook/repeated section
- `[bridge]` - Musical departure
- `[inst-short]` - Short instrumental (0-10s)
- `[inst-medium]` - Medium instrumental (10-20s)
- `[outro]` - Ending section

**Important**: Use ` ; ` (space-semicolon-space) before instrumental tags when they follow lyrical sections.

### Example Format

```
[verse]
Lyrics here
More lyrics
 ; 
[inst-short]
[chorus]
Chorus lyrics here
 ; 
[outro]
```

## Output

- `structured_lyrics.txt` - Processed lyrics
- `{song_title}_ai_cover.flac` - Generated audio (0.8x speed for lofi)
- `{song_title}_music_video.mp4` - Final video (1080x1920)

## GitHub Actions Workflow

The repository includes a workflow to run the entire pipeline automatically.

## License

MIT
