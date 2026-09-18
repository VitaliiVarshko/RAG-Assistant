import time

import requests
import json
from langdetect import detect
from deep_translator import GoogleTranslator  # вместо googletrans
from config import get_chroma_client, SUPPORTED_LANGUAGES
from dotenv import load_dotenv
import os

load_dotenv()


class MultiLangQA:
    def __init__(self, db_path="./chroma_db", mistral_api_key=None):
        self.client, self.embedding_function = get_chroma_client(db_path)
        self.mistral_api_key = mistral_api_key  
        self.translator = GoogleTranslator()
        
        # Connecting to existing collections
        self.collections = {}
        for lang_code in SUPPORTED_LANGUAGES:
            try:
                collection_name = SUPPORTED_LANGUAGES[lang_code]["collection"]
                self.collections[lang_code] = self.client.get_collection(
                    collection_name,
                    embedding_function=self.embedding_function
                )
                print(f"✅ Connected to collection {lang_code.upper()}: {collection_name}")
            except Exception as e:
                print(f"⚠️ Collection {lang_code.upper()} not found: {e}")
                self.collections[lang_code] = None
        
    def detect_language(self, text):
        """Detects the language of the text with improved logic for short phrases"""
        try:
            # If the text is short, add contextual words for detection
            if len(text) < 20:
                # List of characteristic words for Russian and Ukrainian
                ru_words = ['это', 'что', 'как', 'где', 'кто', 'почему', 'зачем', 'когда']
                uk_words = ['це', 'що', 'як', 'де', 'хто', 'чому', 'навіщо', 'коли']
                
                text_lower = text.lower()
                ru_score = sum(1 for word in ru_words if word in text_lower)
                uk_score = sum(1 for word in uk_words if word in text_lower)
                
                if ru_score > uk_score:
                    return 'ru'
                elif uk_score > ru_score:
                    return 'uk'
                # If we couldn't determine the language, use langdetect
                return detect(text)
            else:
                return detect(text)
        except:
            return None
        
    def translate_text(self, text, dest_lang):
        """Translates text to the specified language using GoogleTranslator"""
        try:
            time.sleep(0.5)
            translated = GoogleTranslator(source='auto', target=dest_lang).translate(text)
            return translated
        except Exception as e:
            print(f"⚠️ Error translating: {e}")
            return text  
    
    def search(self, query, language, top_k=3):
        """Search in the collection for the specified language"""
        collection = self.collections.get(language)
        if not collection:
            return None
        
        try:
            results = collection.query(
                query_texts=[query],
                n_results=top_k
            )
            return results
        except Exception as e:
            print(f"❌ Error searching: {e}")
            return None
    
    def format_context(self, results):
        """Formats the search results into context"""
        if not results or not results['documents']:
            return None
        
        context_parts = []
        for i, doc in enumerate(results['documents'][0], 1):
            context_parts.append(f"[{i}] {doc}")
        
        return "\n\n".join(context_parts)
    
    def generate_ollama(self, query, context, language, model="qwen3:1.7b"):
        """Generates a response through Ollama in the required language"""
        system_prompts = {
            "ru": "Используя информацию из контекста, ответь на вопрос на русском языке. Если в контексте нет информации, скажи, что не знаешь.",
            "uk": "Використовуючи інформацію з контексту, дай відповідь на питання українською мовою. Якщо в контексті немає інформації, скажи, що не знаєш."
        }
        
        prompt = f"""{system_prompts.get(language, system_prompts["ru"])}

КОНТЕКСТ:
{context}

ВОПРОС: {query}

ОТВЕТ:"""
        
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7}
        }
        
        try:
            response = requests.post(url, json=payload, timeout=40)
            if response.status_code == 200:
                return response.json()['response']
            else:
                return f"❌ Error: {response.status_code}"
        except Exception as e:
            return f"❌ Error generating response: {e}"





    def generate_mistral(self, query, context, language, model=""):
        """
        Generates a response through the Mistral API
        
        query: user question
        context: context from found documents
        language: response language
        model: Mistral model (mistral-small-latest, mistral-medium-latest, mistral-large-latest)
        """
        if not self.mistral_api_key:
            return "❌ Error: Mistral API key is not specified"
        
        system_prompts = {
            "ru": "Используя информацию из контекста, ответь на вопрос на русском языке. Если в контексте нет информации, скажи, что не знаешь.",
            "uk": "Використовуючи інформацію з контексту, дай відповідь на питання українською мовою. Якщо в контексті немає інформації, скажи, що не знаєш."
        }
        
        prompt = f"""{system_prompts.get(language, system_prompts["ru"])}

КОНТЕКСТ:
{context}

ВОПРОС: {query}

ОТВЕТ:"""
        
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.mistral_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompts.get(language, "Ответь на вопрос, используя контекст.")},
                {"role": "user", "content": f"Контекст:\n{context}\n\nВопрос: {query}"}
            ],
            "temperature": 0.5,
            "max_tokens": 4000
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:

                #print("\n--- information about limits ---")
                #print(f"Осталось токенов на минуту: {response.headers.get('x-ratelimit-remaining-tokens-minute')}")
                #print(f"Лимит токенов в минуту: {response.headers.get('x-ratelimit-limit-tokens-minute')}")
                #print(f"Сброс через (сек): {response.headers.get('x-ratelimit-reset-tokens-minute')}")


                result = response.json()

                # Extracting the response from JSON
                #assistant_message = result['choices'][0]['message']['content']
                #print(f"\nߤ֠Ответ: {assistant_message}")
                
                # Additional information
                #print(f"\nߓСтатистика:")
                #print(f"  - Модель: {result['model']}")
                #print(f"⏱️  Время генерации: {result.get('total_duration', 0) / 1e9:.3f} сек")
               # print(f"  - Токенов использовано: {result['usage']['total_tokens']}")



                return result['choices'][0]['message']['content']
            else:
                return f"❌ Error Mistral API: {response.status_code}\n{response.text}"
        except requests.exceptions.ConnectionError:
            return "❌ Error: Failed to connect to Mistral API"
        except requests.exceptions.Timeout:
            return "❌ Error: Timeout while requesting Mistral API"
        except Exception as e:
            return f"❌ Unexpected error: {e}"


    def answer_question(self, query, top_k=3, generator="ollama", model=None, fallback_to_translation=True):
        """
        The basic method for answering the question of choosing a generator
        """
        print(f"\n🔍 Question: {query}")
        
        # 1. Определяем язык
        query_lang = self.detect_language(query)
        if not query_lang:
            print("⚠️ Failed to detect language, using Russian")
            query_lang = "ru"
        
        print(f"🌍 Question language: {query_lang.upper()}")
        
        # 2. Try to find in the collection for this language
        results = self.search(query, query_lang, top_k)
        
        # 3. If nothing is found OR the language is not supported, try translation
        if (not results or not results['documents']) and fallback_to_translation:
            print(f"ℹ️ Nothing found in {query_lang.upper()}, trying translation...")
            
            # If the question language is not Russian, translate the question
            if query_lang != "ru":
                translated_query = self.translate_text(query, 'ru')
                print(f"🔄 Translating question to Russian: {translated_query}")
                search_query = translated_query
                search_lang = "ru"
            else:
                # If Russian, but nothing found, try Ukrainian
                translated_query = self.translate_text(query, 'uk')
                print(f"🔄 Translating question to Ukrainian: {translated_query}")
                search_query = translated_query
                search_lang = "uk"
            
            # Search in the other collection
            results = self.search(search_query, search_lang, top_k)
            
            # If found in another collection
            if results and results['documents']:
                print(f"✅ Found in collection {search_lang.upper()}")
                context = self.format_context(results)
                
                # Generating a response in the target language
                if generator == "mistral":
                    answer_text = self.generate_mistral(search_query, context, search_lang, model or "mistral-small-latest")
                else:
                    answer_text = self.generate_ollama(search_query, context, search_lang, model or "qwen3:1.7b")
                
                # If the question language does not match the translation language, translate the answer
                if query_lang != search_lang:
                    answer_text = self.translate_text(answer_text, query_lang)
                    print(f"🔄 Translating answer to {query_lang.upper()}")
                
                return answer_text
            
            # If nothing is found and after translation
            return "Sorry, I didn't find any information related to your question."
        
        # 4. If found in the question language collection
        if results and results['documents']:
            print(f"✅ Found in collection {query_lang.upper()}")
            context = self.format_context(results)
            
            # Generating a response in the target language
            if generator == "mistral":
                return self.generate_mistral(query, context, query_lang, model or "mistral-small-latest")
            else:
                return self.generate_ollama(query, context, query_lang, model or "qwen3:1.7b")
        
        # 5. If nothing is found and translation is disabled
        return "Sorry, I didn't find any information related to your question."

    
    def show_stats(self):
        """Shows statistics for all collections"""
        print("\n📊 Multi-language DB Statistics:")
        print("="*40)
        total = 0
        for lang_code, collection in self.collections.items():
            if collection:
                count = collection.count()
                total += count
                lang_name = SUPPORTED_LANGUAGES[lang_code]["name"]
                print(f"   {lang_code.upper()} ({lang_name}): {count} chunks")
        print(f"   Total: {total} chunks")
        print("="*40)

# ============ USAGE ============


if __name__ == "__main__":
    
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    
    
    qa = MultiLangQA(mistral_api_key=MISTRAL_API_KEY)
    qa.show_stats()
    
    # Questions for testing
    questions = [
    #    "Какие услуги вы предоставляете?",
    #    "Сколько стоит создание сайта?",
    #    "Які послуги ви надаєте?",
        "What services do you offer?"
    ]
    
    for question in questions:
        print("\n" + "="*60)
        # Using Mistral for the answer
        answer = qa.answer_question(
            question,
            top_k=5,  # More context for better answers
            generator="mistral",
            model="mistral-small-2603" #2506  # Can use mistral-medium-latest or mistral-large-latest
        )
        print(f"💬 Answer:\n{answer}")
        print("="*60)







