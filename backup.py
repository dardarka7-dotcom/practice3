"""ПР1. Резервное копирование с ротацией, проверкой целостности и восстановлением."""
import hashlib
import json
import shutil
import tarfile
import time
from datetime import datetime
from pathlib import Path
 
SOURCE = Path("company_data")     
BACKUP_DIR = Path("backups")      
KEEP_LAST = 5                     
 
 
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
 
 
def make_manifest(folder):
    """Контрольная сумма каждого файла: {относительный_путь: sha256}."""
    return {str(p.relative_to(folder)): sha256(p)
            for p in sorted(folder.rglob("*")) if p.is_file()}
 
 
def create_backup():
    BACKUP_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive = BACKUP_DIR / f"backup_{stamp}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(SOURCE, arcname=SOURCE.name)
    manifest = {"created": stamp, "archive_sha256": sha256(archive),
                "files": make_manifest(SOURCE)}
    archive.with_suffix("").with_suffix(".json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Создан {archive.name}, файлов: {len(manifest['files'])}, "
          f"размер: {archive.stat().st_size / 1024:.1f} КБ")
    return archive
 
 
def rotate():
    archives = sorted(BACKUP_DIR.glob("backup_*.tar.gz"))
    for old in archives[:-KEEP_LAST]:
        old.unlink()
        old.with_suffix("").with_suffix(".json").unlink(missing_ok=True)
        print(f"[ROTATE] Удалена старая копия {old.name}")
 
 
def verify_restore(archive):
    """Задание 3: Восстанавливает архив во временную папку и выводит подробный отчёт о различиях."""
    manifest_path = archive.with_suffix("").with_suffix(".json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    
    if sha256(archive) != manifest["archive_sha256"]:
        print("[FAIL] Архив повреждён: контрольная сумма не совпадает")
        return False
        
    tmp = Path("restore_test")
    shutil.rmtree(tmp, ignore_errors=True)
    
    with tarfile.open(archive) as tar:
        tar.extractall(tmp, filter="data")
        
    restored = make_manifest(tmp / SOURCE.name)
    shutil.rmtree(tmp)
    
    original_files = manifest["files"]
    if restored == original_files:
        print(f"[OK] Восстановление проверено: {len(restored)} файлов совпадают")
        return True
    
    # Детальный отчёт о различиях (Задание 3)
    print("[FAIL] Восстановленные данные не совпадают с оригиналом:")
    restored_keys = set(restored.keys())
    orig_keys = set(original_files.keys())
    
    missing = orig_keys - restored_keys
    extra = restored_keys - orig_keys
    common = orig_keys & restored_keys
    modified = [k for k in common if restored[k] != original_files[k]]
    
    if missing:
        print(f"  - Отсутствуют файлы ({len(missing)}): {sorted(list(missing))}")
    if extra:
        print(f"  - Лишние файлы ({len(extra)}): {sorted(list(extra))}")
    if modified:
        print(f"  - Изменены файлы ({len(modified)}): {sorted(list(modified))}")
        
    return False


def restore(archive):
    """Задание 4: Восстановление после инцидента с замером времени."""
    start_time = time.perf_counter()
    
    if SOURCE.exists():
        shutil.rmtree(SOURCE)
        print(f"[INFO] Поврежденная папка {SOURCE} удалена.")
        
    with tarfile.open(archive) as tar:
        tar.extractall(path=".", filter="data")
        
    elapsed_time = time.perf_counter() - start_time
    print(f"[OK] Данные успешно восстановлены из {archive.name}")
    print(f"[TIME] Время восстановления: {elapsed_time:.4f} секунд")


if __name__ == "__main__":
    archive = create_backup()
    rotate()
    
    print("\n--- Проверка целостности ---")
    verify_restore(archive)
    
    print("\n--- Моделирование инцидента и восстановления ---")
    buh_folder = SOURCE / "buh"
    if buh_folder.exists():
        shutil.rmtree(buh_folder)
        print(f"[INCIDENT] Папка {buh_folder} случайно удалена сотрудником!")
        
   
    restore(archive)