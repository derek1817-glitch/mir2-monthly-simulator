import json
import os
import bcrypt
from pathlib import Path

def hash_password(password):
    """비밀번호를 bcrypt로 해시"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

def migrate_users():
    """기존 allowed_users.json의 비밀번호를 해시로 변환"""
    
    users_file = Path('users/allowed_users.json')
    backup_file = Path('users/allowed_users_backup.json')
    
    if not users_file.exists():
        print("❌ allowed_users.json을 찾을 수 없습니다")
        return False
    
    print("📂 기존 파일 백업 중...")
    with open(users_file, 'r', encoding='utf-8') as f:
        original_data = json.load(f)
    
    # 백업 저장
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(original_data, f, ensure_ascii=False, indent=2)
    print(f"✅ 백업 완료: {backup_file}")
    
    # 비밀번호 해시 변환
    print("\n🔐 비밀번호 해시 변환 중...")
    migrated_users = {}
    
    for user_id, user_info in original_data.get('users', {}).items():
        password = user_info.get('password', '')
        hashed_password = hash_password(password)
        
        migrated_users[user_id] = {
            "password": hashed_password,
            "name": user_info.get('name', ''),
            "position": user_info.get('position', ''),
            "first_login": user_info.get('first_login', False)
        }
        
        print(f"  ✓ {user_id} ({user_info.get('name', 'N/A')}) - 해시 변환 완료")
    
    # 새 파일 저장
    new_data = {'users': migrated_users}
    with open(users_file, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 마이그레이션 완료!")
    print(f"총 {len(migrated_users)}명의 사용자 비밀번호가 해시 변환되었습니다")
    print(f"변환된 파일: {users_file}")
    print(f"백업 파일: {backup_file}")
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("🔐 비밀번호 해시 마이그레이션 스크립트")
    print("=" * 50)
    
    confirm = input("\n기존 비밀번호를 모두 해시로 변환하시겠습니까? (y/n): ")
    
    if confirm.lower() == 'y':
        migrate_users()
    else:
        print("취소되었습니다")
