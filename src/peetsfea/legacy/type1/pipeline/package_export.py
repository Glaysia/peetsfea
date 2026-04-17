from __future__ import annotations

from pathlib import Path
import zipfile


_FIXED_ZIPINFO_DATETIME = (1980, 1, 1, 0, 0, 0)


def _new_zip_info(filename: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(filename=filename, date_time=_FIXED_ZIPINFO_DATETIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o644 << 16
    return info


def export_design_zip(
    design_id: str,
    aedt_path: Path,
    repro_toml: bytes,
    dataset_toml: bytes,
    source_toml: bytes,
    output_dir: Path,
) -> Path:
    if not aedt_path.exists() or not aedt_path.is_file():
        raise FileNotFoundError(f"AEDT file not found for zip export: {aedt_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"{design_id}.zip"

    aedt_filename = f"{design_id}.aedt"
    repro_filename = f"{design_id}.repro.toml"
    dataset_filename = f"{design_id}.dataset.toml"
    source_filename = f"{design_id}.source.toml"

    aedt_bytes = aedt_path.read_bytes()

    with zipfile.ZipFile(zip_path, mode="w") as zf:
        zf.writestr(_new_zip_info(aedt_filename), aedt_bytes)
        zf.writestr(_new_zip_info(repro_filename), repro_toml)
        zf.writestr(_new_zip_info(dataset_filename), dataset_toml)
        zf.writestr(_new_zip_info(source_filename), source_toml)

    return zip_path


__all__ = ["export_design_zip"]
