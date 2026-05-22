"""
WebBot Versioning — 轻量发布版本管理系统

每次 publish 时生成页面内容快照（不含 header/footer），存入文件系统。
一天只做一个快照：同一页面同一天多次 publish 会覆盖当天的版本。
只对页面内容（body content）做版本，header/footer 由系统模板控制。
版本信息路径：app/versions/pages/<page_safe_path>/v<N>.json
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

# 版本存储根目录（相对于 app/）
VERSIONS_DIR = Path(__file__).parent / "versions" / "pages"
VERSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _safe_path(page_path: str) -> str:
    """将页面路径转为安全的文件系统目录名"""
    return page_path.strip("/").replace("/", "__")


def _page_dir(page_path: str) -> Path:
    """获取页面版本目录"""
    d = VERSIONS_DIR / _safe_path(page_path)
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_next_version(page_path: str) -> int:
    """
    返回下一个版本号。
    一天只做一个快照：如果当天已有版本则复用版本号（覆盖），否则新建。
    """
    pdir = _page_dir(page_path)
    existing = sorted([int(f.name[1:].split(".")[0]) for f in pdir.glob("v*.json")])
    if not existing:
        return 1

    today = datetime.utcnow().strftime("%Y-%m-%d")
    # 从大到小检查，找今天的版本
    for v in reversed(existing):
        meta_path = pdir / f"v{v}.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if meta.get("created_at", "").startswith(today):
                    return v  # 复用当天版本号（覆盖）
            except (json.JSONDecodeError, OSError):
                continue
    return (max(existing) if existing else 0) + 1


def save_version(page_path: str, content: str, page_id: str,
                 page_title: str, page_language: str, version: int,
                 author: str = "system", notes: str = "") -> dict:
    """
    保存一个发布版本快照。
    只存页面内容（body），不存 header/footer。
    返回 metadata dict.
    """
    pdir = _page_dir(page_path)
    now = datetime.utcnow().isoformat() + "Z"

    # 写 JSON metadata（内嵌 content，不单独写 .html 文件）
    meta = {
        "version": version,
        "page_id": page_id,
        "page_path": page_path,
        "page_title": page_title,
        "language": page_language,
        "content_size": len(content.encode("utf-8")),
        "created_at": now,
        "author": author,
        "notes": notes,
        # 内容直接嵌入（header/footer 由系统模板控制不保存）
        "content": content,
    }
    meta_path = pdir / f"v{version}.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # 更新 manifest
    _update_manifest(page_path, meta)

    return meta


def _update_manifest(page_path: str, meta: dict):
    """将最新版本信息写入全局 manifest"""
    manifest_path = VERSIONS_DIR / ".." / "manifest.json"
    manifest_path = manifest_path.resolve()
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {"pages": {}, "updated_at": meta["created_at"]}

    safe = _safe_path(page_path)
    if safe not in manifest["pages"]:
        manifest["pages"][safe] = {
            "page_path": page_path,
            "versions": []
        }
    if meta["version"] not in manifest["pages"][safe]["versions"]:
        manifest["pages"][safe]["versions"].append(meta["version"])
        manifest["pages"][safe]["versions"].sort()
    manifest["pages"][safe]["latest"] = meta["version"]
    manifest["pages"][safe]["latest_meta"] = {
        "version": meta["version"],
        "created_at": meta["created_at"],
        "author": meta["author"],
        "content_size": meta["content_size"],
    }
    manifest["updated_at"] = meta["created_at"]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def get_versions(page_path: str) -> list:
    """获取指定页面的所有版本信息列表（按版本号降序，不含 content 正文以节省带宽）"""
    pdir = _page_dir(page_path)
    versions = []
    for f in sorted(pdir.glob("v*.json"), reverse=True):
        try:
            meta = json.loads(f.read_text(encoding="utf-8"))
            # 列表返回时移除内嵌 content（仅 API 单版本查询时提供）
            meta.pop("content", None)
            versions.append(meta)
        except (json.JSONDecodeError, OSError):
            continue
    return versions


def get_version(page_path: str, version: int) -> Optional[dict]:
    """获取指定版本的 metadata + content"""
    pdir = _page_dir(page_path)
    meta_path = pdir / f"v{version}.json"
    if not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return meta


def rollback_to_version(page_path: str, version: int) -> Optional[str]:
    """
    回滚到指定版本，返回该版本的 content（页面正文）。
    由调用方负责将 content 重新渲染 + publish。
    """
    snap = get_version(page_path, version)
    if snap is None:
        return None
    return snap.get("content")


def delete_page_versions(page_path: str) -> bool:
    """删除页面的所有版本（用于级联删除）"""
    pdir = _page_dir(page_path)
    if pdir.exists() and pdir.is_dir():
        shutil.rmtree(pdir)
        return True
    return False


def get_all_versions_summary() -> list:
    """获取所有有版本的页面摘要（用于 dashboard）"""
    manifest_path = VERSIONS_DIR / ".." / "manifest.json"
    manifest_path = manifest_path.resolve()
    if not manifest_path.exists():
        return []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result = []
    for safe, info in manifest.get("pages", {}).items():
        result.append({
            "page_path": info["page_path"],
            "version_count": len(info.get("versions", [])),
            "latest_version": info.get("latest", 0),
            "latest_at": info.get("latest_meta", {}).get("created_at", ""),
            "latest_size": info.get("latest_meta", {}).get("content_size", 0),
        })
    return sorted(result, key=lambda x: x["latest_at"], reverse=True)


def assemble_page_html(content: str, head: str, header: str, footer: str,
                        date_modified: str, language: str, title: str,
                        page_path: str, header_en: str = None,
                        header_fr: str = None, date_modified_html: str = None) -> str:
    """
    将页面内容 + 模板片段组装成完整 HTML 页面。
    header/footer 由系统控制，内容来自版本记录。
    回滚时使用此函数重建完整页面。
    """
    template = (
        "<!DOCTYPE html>\n"
        f"<html lang=\"{language}\">\n"
        f"{head}\n"
        f"{header}\n"
        "<body>\n"
        '<main property="mainContentOfPage" resource="#wb-main" typeof="WebPageElement" class="container">\n'
        f"{content}\n"
        f"{date_modified_html or ''}\n"
        "</main>\n"
        f"{footer}\n"
        "</body>\n"
        "</html>"
    )
    return template
