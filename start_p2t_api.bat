@echo off
cd  C:\Users\user\Documents\sss001
call venv\Scripts\activate
python p2t_api_server.py 


#  cd  C:\Users\user\Documents\sss001
# .\cloudflared tunnel --url http://localhost:5001


# netstat -ano | findstr :5001
# tasklist | findstr cloudflared

# git add .
#git commit -m " update"
#git push
