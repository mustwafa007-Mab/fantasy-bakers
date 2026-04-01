# Deployment Guide: Sharing the Model

To let the board try the system themselves, you have two options:

## Option A: Temporary Public Link (Easiest)
Use this if you just want to send a link valid for 2 hours during the meeting.

1. **Download ngrok**: Go to [ngrok.com](https://ngrok.com) and sign up (free).
2. **Start your app**:
   ```powershell
   uvicorn app:app --reload
   ```
3. **Start ngrok** (in a new terminal):
   ```powershell
   ngrok http 8000
   ```
4. **Copy the Link**: ngrok will give you a URL like `https://a1b2-c3d4.ngrok-free.app`.
5. **Send it**: Anyone with this link can see your dashboard.

## Option B: Permanent Cloud Hosting (Professional)
Use this for a permanent demo link.

1. **Create a GitHub Repository**: Upload this folder to GitHub.
2. **Sign up for Render**: Go to [render.com](https://render.com).
3. **New Web Service**:
   - Connect your GitHub repo.
   - Build Command: `pip install fastapi uvicorn pydantic`
   - Start Command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. **Deploy**: Render will give you a URL like `https://fantasy-ai-erp.onrender.com`.

**Note**: For the database, you will need to create a real project on [Supabase.com](https://supabase.com) and update the `app.py` to use `supabase-py` instead of the local memory mock.
