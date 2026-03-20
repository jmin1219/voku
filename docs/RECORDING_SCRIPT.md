# Screen Recording Script — 60 seconds

> Record with QuickTime (Cmd+Shift+5 → Record Selected Portion).
> Use your local 869-trace database. Resolution: 1920×1080 or retina equivalent.
> No voiceover needed — the GIF/video is silent. The README text does the narrating.

## Before Recording
- Start backend: `cd backend && source venv/bin/activate && uvicorn app.main:app --reload`
- Start frontend: `cd frontend && NODE_ENV=development npm run dev`
- Open http://localhost:5173
- Make sure you have conversations loaded (869 traces)
- Browser: hide bookmarks bar, use clean window

## The Take (aim for ~60s, trim in post)

### 0-5s: Chat view
Show the chat interface with a recent conversation visible. Let it breathe for a moment — the viewer needs to orient.

### 5-15s: Ask a question
Type: "What have I been going back and forth on?"
Let the response stream in. Context markers [1] [2] [3] appear.

### 15-25s: Open phase space
Hit Cmd+Space. The 3D graph slides in from the right. Slowly orbit — let the cluster structure be visible. Retrieved nodes should glow.

### 25-40s: Explore
- Hover over a few traces (content previews appear)
- Click on one (detail panel)
- Zoom out to show the full topology
- Zoom into a dense cluster

### 40-50s: Show temporal digest
Type `/digest` or click the digest button. Let the narrative generate — it pulls from across the whole graph.

### 50-60s: Final orbit
Switch back to the phase space. Slow orbit showing the full structure. End on a wide shot.

## Post-Recording
- Convert to GIF (gifski, ffmpeg, or CloudConvert) — aim for <10MB
- OR keep as MP4 and use GitHub's video embedding
- Trim dead time, speed up typing if needed
- Save as: `docs/demo.gif` or `docs/demo.mp4`
