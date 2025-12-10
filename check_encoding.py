import sys
try:
    with open('bot_head_snapshot.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(f"✅ File berhasil dibaca dengan UTF-8 ({len(lines)} lines)")
except UnicodeDecodeError as e:
    print(f"❌ UTF-8 error at position {e.start}: {e.reason}")
    try:
        with open('bot_head_snapshot.py', 'r', encoding='utf-16') as f:
            lines = f.readlines()
            print(f"✅ File dapat dibaca dengan UTF-16 ({len(lines)} lines)")
    except Exception as e2:
        print(f"❌ UTF-16 juga gagal: {e2}")
