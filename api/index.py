# ... (semua kode Flask Anda sebelumnya) ...

# Entry point untuk Fly.io
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)

# Pastikan 'app' terekspos di module level
app
