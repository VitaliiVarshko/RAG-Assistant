from multi_lang_loader import MultiLangLoader
from site_config import SITE_CONFIG

def test_crawl():
    loader = MultiLangLoader()
    
    print("🧪 TEST MODE: Only the main page will be processed")
    print("="*60)
    
    # ✅ We use the configuration from site_config.py
    config = SITE_CONFIG["uk"].copy()
    config["max_pages"] = 1  # Limit to one page
    
    try:
        # ✅ We pass the language code and configuration
        loader.crawl_website("uk", config)
        print("\n✅ Test crawling completed!")
        print("📊 Check the results in ChromaFlowStudio")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_crawl()