import os
import time
import hashlib
from langdetect import detect
from langchain_text_splitters import RecursiveCharacterTextSplitter
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from config import (
    get_chroma_client,
    get_collection,
    SUPPORTED_LANGUAGES,
    CHUNK_SIZE,
    CHUNK_OVERLAP
)


class ImprovedCrawler:
    def __init__(self, loader):
        self.loader = loader
        self.visited_urls = set()
        self.failed_urls = set()
        self.processed_pages = 0
        self.stats = {
            "total_pages": 0,
            "successful": 0,
            "failed": 0,
            "empty_content": 0,
            "duplicates": 0
        }
    
    def is_valid_url(self, url, base_url, config):
        """Проверяет, стоит ли обрабатывать URL"""
        parsed = urlparse(url)
        
        # Let's check that it's the same domain.
        if parsed.netloc != urlparse(base_url).netloc:
            return False
        
        # Let's check that it's not a link to a file
        if any(url.endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.zip', '.doc', '.docx']):
            return False
        
        # Let's check the exclusions
        for pattern in config.get("exclude_patterns", []):
            if pattern in url:
                return False
        
        # If there are include_patterns, let's check them
        include_patterns = config.get("include_patterns", [])
        if include_patterns:
            return any(pattern in url for pattern in include_patterns)
        
        return True
    
    def extract_main_content(self, soup, config):
        """Extracts the main content of the page"""
        from site_config import CONTENT_SELECTORS
        
        # Let's remove unnecessary elements
        for selector in CONTENT_SELECTORS.get("exclude", []):
            for element in soup.select(selector):
                element.decompose()
        
        # Let's try to find the main content by selectors
        content = None
        for selector in CONTENT_SELECTORS.get("main_content", []):
            elements = soup.select(selector)
            if elements:
                content = " ".join([el.get_text(separator='\n') for el in elements])
                break
        
        # If we didn't find it by selectors, we'll take all the text
        if not content:
            content = soup.get_text(separator='\n')
        
        # Let's clean it up
        content = '\n'.join([line.strip() for line in content.splitlines() if line.strip()])
        
        return content
    
    def get_page_title(self, soup, url):
        """Extracts the page title"""
        from site_config import CONTENT_SELECTORS
        
        # Let's try to find it by selectors
        for selector in CONTENT_SELECTORS.get("title", []):
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        # If we didn't find it, use the title
        if soup.title:
            return soup.title.get_text(strip=True)
        
        # In the worst case, use the URL
        return url.split('/')[-1].replace('-', ' ').replace('_', ' ').title()
    
    def crawl_page(self, url, config, depth=0, max_depth=3):
        """Recursively crawl pages with a depth limit"""
        if depth > max_depth:
            return
        
        if url in self.visited_urls:
            self.stats["duplicates"] += 1
            return
        
        if url in self.failed_urls:
            return
        
        self.visited_urls.add(url)
        self.stats["total_pages"] += 1
        
        try:
            # Adding headers to simulate a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': f'{config["language"]}-{config["language"].upper()},en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                print(f"   ⚠️ Error {response.status_code} for {url}")
                self.failed_urls.add(url)
                self.stats["failed"] += 1
                return
            
            # Parsing HTML
            soup = BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')
            
            # Extracting content
            content = self.extract_main_content(soup, config)
            
            if not content or len(content) < 100:  # Skipping too short pages
                print(f"   📄 Skipped page (too short): {url}")
                self.stats["empty_content"] += 1
                return
            
            # Extracting the title
            title = self.get_page_title(soup, url)
            
            # Saving the content
            metadata = {
                "url": url,
                "title": title,
                "language": config["language"],
                "depth": depth,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "content_length": len(content)
            }
            
            # Adding to the database
            self.loader.add_texts(
                texts=[content],
                language=config["language"],
                metadatas=[metadata],
                source=f"website_{config['language']}"
            )
            
            self.processed_pages += 1
            self.stats["successful"] += 1
            print(f"   ✅ [{self.processed_pages}] {title[:50]}... ({len(content)} characters) - {url}")
            
            # Finding new links
            links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href:
                    full_url = urljoin(url, href)
                    if self.is_valid_url(full_url, config["url"], config):
                        links.append(full_url)
            
            # Limiting the number of links to process
            links = links[:20]
            
            # Recursively crawling the found links
            for link_url in links[:10]:
                if link_url not in self.visited_urls:
                    time.sleep(0.5)
                    self.crawl_page(link_url, config, depth + 1, max_depth)
            
        except requests.exceptions.Timeout:
            print(f"   ⏱️ Timeout for {url}")
            self.failed_urls.add(url)
            self.stats["failed"] += 1
        except Exception as e:
            print(f"   ❌ Error for {url}: {str(e)[:100]}")
            self.failed_urls.add(url)
            self.stats["failed"] += 1
    
    def run_crawl(self, config):
        """Runs the crawling process for the specified configuration"""
        start_url = config.get("url")
        if not start_url:
            print(f"❌ Error: No URL in configuration")
            return
        
        language = config.get("language", "unknown")
        print(f"\n🌐 Starting crawl for {language} (max. {config.get('max_pages', 100)} pages)")
        print("-" * 60)
        
        start_time = time.time()
        
        # We launch the crawl from the main page
        self.crawl_page(start_url, config, depth=0, max_depth=3)
        
        elapsed_time = time.time() - start_time
        
        
        print("\n" + "="*60)
        print("📊 CRAWLING STATISTICS")
        print("="*60)
        print(f"   Pages processed: {self.stats['total_pages']}")
        print(f"   Successfully loaded: {self.stats['successful']}")
        print(f"   Errors: {self.stats['failed']}")
        print(f"   Empty content: {self.stats['empty_content']}")
        print(f"   Duplicates: {self.stats['duplicates']}")
        print(f"   Execution time: {elapsed_time:.2f} sec.")
        print("="*60)
        
        return self.stats





class MultiLangLoader:
    def __init__(self, db_path="./chroma_db"):
        self.client, self.embedding_function = get_chroma_client(db_path)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # We create collections for each language
        self.collections = {}
        for lang_code in SUPPORTED_LANGUAGES:
            self.collections[lang_code] = get_collection(
                self.client, self.embedding_function, lang_code
            )
        
        print("✅ Multilingual bootloader initialized")
        for lang_code, collection in self.collections.items():
            print(f"   {lang_code.upper()}: {collection.count()} documents")
            
    


    def add_texts(self, texts, language, metadatas=None, source="manual"):
        """
        Adds texts to the collection for the specified language

        texts: list of texts
        language: language code ("ru" or "uk")
        metadatas: list of dictionaries with metadata
        source: source of the texts
        """
        if not texts:
            print("❌ No texts to add")
            return
        
        collection = self.collections.get(language)
        if not collection:
            print(f"❌ Unsupported language: {language}")
            return
        
        # We create chunks from the texts
        all_chunks = []
        all_metadatas = []
        all_ids = []
        
        for i, text in enumerate(texts):
            chunks = self.text_splitter.split_text(text)
            all_chunks.extend(chunks)
            
            # Metadata for each chunk
            for j, chunk in enumerate(chunks):
                if metadatas and i < len(metadatas):
                    meta = metadatas[i].copy()
                    meta.update({
                        "language": language,
                        "source": source,
                        "chunk_index": j,
                        "total_chunks": len(chunks)
                    })
                else:
                    meta = {
                        "language": language,
                        "source": source,
                        "chunk_index": j,
                        "total_chunks": len(chunks)
                    }
                all_metadatas.append(meta)
                
                # ID based on the hash of the content and language
                chunk_hash = hashlib.md5(f"{language}_{chunk}".encode()).hexdigest()[:16]
                all_ids.append(f"{language}_{chunk_hash}")
        
        # Add to the collection with duplicate checking
        try:
            # Get existing IDs to avoid adding duplicates
            existing = collection.get()
            existing_ids = set(existing['ids']) if existing['ids'] else set()
            
            new_chunks = []
            new_metadatas = []
            new_ids = []
            
            for chunk, meta, doc_id in zip(all_chunks, all_metadatas, all_ids):
                if doc_id not in existing_ids:
                    new_chunks.append(chunk)
                    new_metadatas.append(meta)
                    new_ids.append(doc_id)
            
            if new_chunks:
                collection.add(
                    documents=new_chunks,
                    metadatas=new_metadatas,
                    ids=new_ids
                )
                print(f"✅ Added {len(new_chunks)} new chunks to the collection {language.upper()}")
            else:
                print(f"ℹ️ All chunks already exist in the collection {language.upper()}")
                
        except Exception as e:
            print(f"❌ Error adding chunks: {e}")
            

    def crawl_website(self, language_code, custom_config=None):
        """
        Runs website crawling for the specified language
        """
        # If a language code is passed, we take the configuration from SITE_CONFIG
        if isinstance(language_code, str) and not custom_config:
            from site_config import SITE_CONFIG
            config = SITE_CONFIG.get(language_code)
            if not config:
                print(f"❌ No configuration found for language {language_code}")
                return
        else:
            # If a configuration is passed, use it
            config = custom_config
        
        # Check that the configuration contains a URL
        if not config or not config.get("url"):
            print(f"❌ Error: No URL found in configuration for language {language_code}")
            print(f"   Received: {config}")
            return
        
        print(f"🌐 Starting crawl for {config.get('language', language_code)} (max. {config.get('max_pages', 100)} pages)")
        
        # Создаём экземпляр краулера и запускаем
        crawler = ImprovedCrawler(self)
        return crawler.run_crawl(config)

    
    def load_from_files(self, folder_path, language):
        """
        Loads texts from files in a folder
        
        folder_path: path to the folder with text files
        language: language code
        """
        texts = []
        metadatas = []
        
        for filename in os.listdir(folder_path):
            if filename.endswith('.txt'):
                file_path = os.path.join(folder_path, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    texts.append(content)
                    metadatas.append({
                        "source": filename,
                        "language": language
                    })
                    print(f"📄 Loaded file: {filename} ({len(content)} characters)")
                except Exception as e:
                    print(f"⚠️ Error reading {filename}: {e}")
        
        if texts:
            self.add_texts(texts, language, metadatas, source="file")
        else:
            print(f"❌ No files found in {folder_path}")
    
    def show_stats(self):
        """Shows statistics for all collections"""
        print("\n📊 Statistics for the multilingual DB:")
        print("="*40)
        total = 0
        for lang_code, collection in self.collections.items():
            count = collection.count()
            total += count
            lang_name = SUPPORTED_LANGUAGES[lang_code]["name"]
            print(f"   {lang_code.upper()} ({lang_name}): {count} chunks")
        print(f"   Total: {total} chunks")
        print("="*40)

# ============ USAGE ============

if __name__ == "__main__":
    loader = MultiLangLoader()
    
    # OPTION 1: Loading from files
    loader.load_from_files("sample_data/ru", "ru")
    loader.load_from_files("sample_data/uk", "uk")
    
    # OPTION 2: Crawling a website (uncomment to use)
    # loader.crawl_website("https://your-site.ru", "ru", max_pages=50)
    # loader.crawl_website("https://your-site.ua", "uk", max_pages=50)
    
    loader.show_stats()