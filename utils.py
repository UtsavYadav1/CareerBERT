try:
    from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine_similarity
    from sklearn.feature_extraction.text import TfidfVectorizer as SklearnTfidfVectorizer
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import string

nltk.download('stopwords')
nltk.download('punkt')
# Use the punkt tokenizer directly instead of loading from pickle
SENT_DETECTOR = nltk.tokenize.PunktSentenceTokenizer()

def calculate_cosine_similarity(sentences1, sentences2):
    # Convert input to list if it's a single string
    if isinstance(sentences1, str):
        sentences1 = [sentences1]
    if isinstance(sentences2, str):
        sentences2 = [sentences2]
    
    # Check if inputs are empty
    if not sentences1 or not sentences2:
        print("Empty input detected")
        return 0.0
    
    # Filter out empty strings
    sentences1 = [s for s in sentences1 if s and s.strip()]
    sentences2 = [s for s in sentences2 if s and s.strip()]
    
    if not sentences1 or not sentences2:
        print("No valid text after filtering")
        return 0.0
    
    print(f"Comparing {len(sentences1)} sentences with {len(sentences2)} sentences")
    print(f"Text1: {sentences1[0][:100]}...")
    print(f"Text2: {sentences2[0][:100]}...")
    
    # Prefer scikit-learn TF-IDF + cosine if available; otherwise use fallbacks
    if SKLEARN_AVAILABLE:
        try:
            # Use optimized TF-IDF vectorizer for better similarity scores
            vectorizer = SklearnTfidfVectorizer(
                min_df=1,
                max_df=0.8,
                ngram_range=(1, 3),
                stop_words=None,
                lowercase=True,
                token_pattern=r'\b\w+\b',
                sublinear_tf=True,
                use_idf=True,
                smooth_idf=True
            )

            # Combine all text for fitting
            all_text = sentences1 + sentences2
            print(f"Combined text length: {len(all_text)}")

            # Fit and transform the text data
            vectors = vectorizer.fit_transform(all_text)
            vectors_array = vectors.toarray()

            print(f"Vector shape: {vectors_array.shape}")

            # Split vectors for comparison
            vec1 = vectors_array[:len(sentences1)]
            vec2 = vectors_array[len(sentences1):]

            # Calculate similarity
            similarity = sklearn_cosine_similarity(vec1, vec2)
            print(f"Raw similarity matrix: {similarity}")

            # Get the maximum similarity (best match)
            max_similarity = float(similarity.max())
            print(f"Max similarity: {max_similarity}")

            # Scale the result to be more meaningful (0-100 range)
            if max_similarity > 0:
                percentage_similarity = max_similarity * 100
                if percentage_similarity < 10:
                    scaled_similarity = min(percentage_similarity * 8, 100)
                elif percentage_similarity < 30:
                    scaled_similarity = min(percentage_similarity * 3, 100)
                else:
                    scaled_similarity = min(percentage_similarity * 1.5, 100)

                print(f"Raw similarity: {max_similarity:.4f}")
                print(f"Percentage similarity: {percentage_similarity:.2f}")
                print(f"Scaled similarity: {scaled_similarity:.2f}")
                return scaled_similarity / 100
            else:
                print("No similarity found, trying word overlap")
                return calculate_word_overlap_similarity(sentences1, sentences2)

        except Exception as e:
            print(f"Error in TF-IDF similarity calculation: {str(e)}")
            # Fall through to non-sklearn similarity

    # Fallbacks when scikit-learn is unavailable or errors occur
    try:
        return calculate_word_overlap_similarity(sentences1, sentences2)
    except Exception as e2:
        print(f"Error in fallback similarity calculation: {str(e2)}")
        try:
            return calculate_keyword_similarity(sentences1, sentences2)
        except Exception as e3:
            print(f"Error in keyword similarity calculation: {str(e3)}")
            return 0.0

def calculate_word_overlap_similarity(sentences1, sentences2):
    """Fallback similarity calculation based on word overlap"""
    print("Using word overlap similarity method")
    
    # Combine all sentences
    text1 = ' '.join(sentences1).lower()
    text2 = ' '.join(sentences2).lower()
    
    print(f"Text1 length: {len(text1)}")
    print(f"Text2 length: {len(text2)}")
    
    # Remove punctuation and split into words
    import string
    text1_words = set(text1.translate(str.maketrans('', '', string.punctuation)).split())
    text2_words = set(text2.translate(str.maketrans('', '', string.punctuation)).split())
    
    print(f"Text1 words: {len(text1_words)}")
    print(f"Text2 words: {len(text2_words)}")
    
    # Remove stop words
    stop_words = set(stopwords.words('english'))
    text1_words = text1_words - stop_words
    text2_words = text2_words - stop_words
    
    print(f"After stopword removal - Text1: {len(text1_words)}, Text2: {len(text2_words)}")
    
    # Calculate Jaccard similarity
    if not text1_words and not text2_words:
        print("No words after stopword removal")
        return 0.0
    
    intersection = len(text1_words.intersection(text2_words))
    union = len(text1_words.union(text2_words))
    
    print(f"Intersection: {intersection}, Union: {union}")
    
    if union == 0:
        print("Union is 0")
        return 0.0
    
    jaccard_similarity = intersection / union
    print(f"Jaccard similarity: {jaccard_similarity}")
    
    # Convert to percentage and apply better scaling
    percentage_similarity = jaccard_similarity * 100
    print(f"Percentage similarity: {percentage_similarity:.2f}")
    
    # Apply aggressive scaling for word overlap method
    if percentage_similarity < 5:
        # For very low similarities, boost significantly
        scaled_similarity = min(percentage_similarity * 15, 100)
    elif percentage_similarity < 15:
        # For low similarities, moderate boost
        scaled_similarity = min(percentage_similarity * 6, 100)
    elif percentage_similarity < 30:
        # For medium similarities, light boost
        scaled_similarity = min(percentage_similarity * 3, 100)
    else:
        # For higher similarities, minimal boost
        scaled_similarity = min(percentage_similarity * 1.5, 100)
    
    print(f"Scaled similarity: {scaled_similarity:.2f}")
    return scaled_similarity / 100  # Return as 0-1 range

def calculate_keyword_similarity(sentences1, sentences2):
    """Final fallback similarity calculation based on keyword matching"""
    print("Using keyword similarity method")
    
    # Combine all sentences
    text1 = ' '.join(sentences1).lower()
    text2 = ' '.join(sentences2).lower()
    
    # Define important keywords for job matching
    important_keywords = [
        'python', 'java', 'javascript', 'react', 'angular', 'node', 'sql', 'database',
        'machine learning', 'ai', 'data science', 'analytics', 'programming', 'development',
        'software', 'engineer', 'developer', 'analyst', 'manager', 'lead', 'senior',
        'experience', 'skills', 'project', 'team', 'leadership', 'communication',
        'problem solving', 'analysis', 'design', 'implementation', 'testing', 'deployment'
    ]
    
    # Count keyword matches
    matches = 0
    total_keywords = len(important_keywords)
    
    for keyword in important_keywords:
        if keyword in text1 and keyword in text2:
            matches += 1
    
    # Calculate similarity based on keyword matches
    if total_keywords == 0:
        return 0.0
    
    keyword_similarity = matches / total_keywords
    print(f"Keyword matches: {matches}/{total_keywords}")
    print(f"Keyword similarity: {keyword_similarity:.4f}")
    
    # Scale to meaningful range
    scaled_similarity = min(keyword_similarity * 200, 100)  # Boost significantly
    print(f"Scaled keyword similarity: {scaled_similarity:.2f}")
    return scaled_similarity / 100  # Return as 0-1 range

def preprocess_sentence(sentence):
    # Convert the sentence to lowercase
    sentence = sentence.lower()
    
    # Remove punctuation
    sentence = sentence.translate(str.maketrans('', '', string.punctuation))
    
    # Tokenize the sentence into words
    words = word_tokenize(sentence)
    
    # Remove stop words
    stop_words = set(stopwords.words('english'))
    words = [word for word in words if word not in stop_words]
    
    # Join the words back into a single string
    sentence = ' '.join(words)
    
    return sentence

def split_into_sentences(text):
    # Replace the bullet points with a period
    text = text.replace(' ● ', '. ')

    # Split the text into sentences
    sentences = text.split('. ')

    return sentences