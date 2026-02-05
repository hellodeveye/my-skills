#!/usr/bin/env python3
"""
Image processing for blog posts - Fetch og:image and upload to R2
Usage: python3 process_images.py --post ~/projects/blog/source/_posts/YYYY-MM-DD.md
"""

import argparse
import os
import re
import sys
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

def extract_og_image(html, base_url):
    """Extract og:image or twitter:image from HTML"""
    patterns = [
        r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']',
        r'<meta[^>]*name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']twitter:image["\']',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return urljoin(base_url, match.group(1))
    
    return None

def download_image(url, temp_dir=None):
    """Download image to temporary file"""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
        content_type = resp.headers.get('Content-Type', '')
        
        # Determine extension
        if 'webp' in content_type:
            ext = '.webp'
        elif 'png' in content_type:
            ext = '.png'
        elif 'gif' in content_type:
            ext = '.gif'
        else:
            ext = '.jpg'
        
        # Save to temp file
        import os
        if temp_dir is None:
            temp_dir = tempfile.gettempdir()
        
        temp_path = os.path.join(temp_dir, f"blog-image-{hash(url)}{ext}")
        with open(temp_path, 'wb') as f:
            f.write(data)
        
        return temp_path

def process_post_images(post_path, r2_upload_func=None):
    """
    Process all images for a blog post
    
    Args:
        post_path: Path to markdown file
        r2_upload_func: Upload function from r2-upload skill (optional)
    
    Returns:
        List of (article_url, image_url) tuples
    """
    post_path = Path(post_path)
    content = post_path.read_text(encoding="utf-8")
    
    # Find article links
    article_links = re.findall(r'\[原文链接\]\(([^)]+)\)', content)
    
    results = []
    
    for i, article_url in enumerate(article_links):
        try:
            print(f"Processing {i+1}/{len(article_links)}: {article_url[:60]}...")
            
            # Fetch article
            req = urllib.request.Request(article_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            
            # Extract og:image
            image_url = extract_og_image(html, article_url)
            
            if not image_url:
                print(f"  No og:image found")
                continue
            
            print(f"  Found image: {image_url[:60]}...")
            
            # Upload to R2 if function provided
            if r2_upload_func:
                # Generate key from post date
                date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', post_path.name)
                if date_match:
                    year, month, day = date_match.groups()
                    key = f"images/{year}/{month}/{day}/article-{i:02d}.jpg"
                else:
                    key = f"images/article-{i:02d}.jpg"
                
                # Download and upload
                temp_path = download_image(image_url)
                try:
                    public_url = r2_upload_func(temp_path, key=key, make_public=True)
                    print(f"  Uploaded: {public_url}")
                    
                    # Insert into content
                    img_tag = f'<img src="{public_url}" alt="配图" style="max-width:100%;height:auto;margin:10px 0;">'
                    
                    # Find the section for this article and insert image
                    pattern = rf"(### [^\n]+\n\n)(?=.*\[原文链接\]\({re.escape(article_url)}\))"
                    if re.search(pattern, content, re.DOTALL):
                        content = re.sub(pattern, rf"\1{img_tag}\n\n", content, count=1, flags=re.DOTALL)
                    
                    results.append((article_url, public_url))
                finally:
                    import os
                    os.unlink(temp_path)
            else:
                results.append((article_url, image_url))
        
        except Exception as e:
            print(f"  Error: {e}")
    
    # Save updated content
    post_path.write_text(content, encoding="utf-8")
    print(f"\nUpdated: {post_path}")
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Process blog post images")
    parser.add_argument("--post", required=True, help="Path to markdown file")
    parser.add_argument("--no-upload", action="store_true", help="Only fetch image URLs, don't upload")
    
    args = parser.parse_args()
    
    # Try to import r2-upload
    upload_func = None
    if not args.no_upload:
        r2_candidates = []
        env_dir = os.environ.get("R2_UPLOAD_SKILL_DIR", "").strip()
        if env_dir:
            r2_candidates.append(Path(env_dir))
        # Try sibling directory to this skill (../r2-upload)
        r2_candidates.append(Path(__file__).resolve().parents[1].parent / "r2-upload")

        for r2_dir in r2_candidates:
            scripts_dir = r2_dir / "scripts"
            if not scripts_dir.exists():
                continue
            sys.path.insert(0, str(scripts_dir))
            try:
                from upload import upload_file
                upload_func = upload_file
                print(f"Using r2-upload skill for image hosting ({r2_dir})")
                break
            except ImportError:
                continue

        if upload_func is None:
            print("Warning: r2-upload skill not available, will only fetch URLs")
            print("Set R2_UPLOAD_SKILL_DIR to the r2-upload folder to enable uploads.")
    
    # Process images
    results = process_post_images(args.post, upload_func)
    
    print(f"\nProcessed {len(results)} images")
    for article, image in results:
        print(f"  - {article[:50]}... -> {image[:50]}...")

if __name__ == "__main__":
    main()
