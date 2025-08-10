import re
from typing import List, Dict, Any, Tuple
from collections import Counter
import hashlib
from datetime import datetime
import json

class MLService:
    def __init__(self):
        self.content_cache = {}
        self.topic_keywords = {
            'technology': ['ai', 'machine learning', 'python', 'javascript', 'react', 'database', 'cloud', 'api'],
            'business': ['startup', 'investment', 'market', 'revenue', 'profit', 'strategy', 'management'],
            'health': ['medical', 'healthcare', 'treatment', 'medicine', 'doctor', 'patient', 'symptoms'],
            'education': ['learning', 'course', 'student', 'teacher', 'school', 'university', 'education'],
            'sports': ['football', 'basketball', 'tennis', 'game', 'player', 'team', 'championship'],
            'entertainment': ['movie', 'music', 'celebrity', 'film', 'actor', 'director', 'album'],
            'politics': ['government', 'election', 'policy', 'president', 'congress', 'vote', 'law'],
            'science': ['research', 'study', 'experiment', 'discovery', 'scientific', 'laboratory']
        }
    
    def analyze_content(self, text: str) -> Dict[str, Any]:
        """Comprehensive content analysis"""
        if not text or len(text.strip()) < 10:
            return self._empty_analysis()
        
        # Basic text analysis
        words = self._tokenize(text)
        sentences = self._split_sentences(text)
        
        analysis = {
            'basic_stats': self._basic_text_stats(text, words, sentences),
            'readability': self._calculate_readability(text, words, sentences),
            'sentiment': self._analyze_sentiment(text),
            'topics': self._identify_topics(text),
            'keywords': self._extract_keywords(words),
            'content_type': self._classify_content_type(text),
            'language_detection': self._detect_language(text),
            'duplicate_score': self._calculate_duplicate_score(text),
            'summary': self._generate_summary(text, sentences),
            'entities': self._extract_entities(text),
            'metadata': {
                'analyzed_at': datetime.utcnow().isoformat(),
                'text_length': len(text),
                'word_count': len(words),
                'sentence_count': len(sentences)
            }
        }
        
        return analysis
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words"""
        # Remove special characters and convert to lowercase
        cleaned = re.sub(r'[^\w\s]', '', text.lower())
        words = cleaned.split()
        return [word for word in words if len(word) > 2]  # Filter short words
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _basic_text_stats(self, text: str, words: List[str], sentences: List[str]) -> Dict[str, Any]:
        """Calculate basic text statistics"""
        if not words:
            return {}
        
        word_freq = Counter(words)
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        return {
            'total_words': len(words),
            'unique_words': len(word_freq),
            'avg_word_length': round(avg_word_length, 2),
            'avg_sentence_length': round(len(words) / len(sentences), 2) if sentences else 0,
            'most_common_words': word_freq.most_common(10),
            'vocabulary_diversity': round(len(word_freq) / len(words), 3)
        }
    
    def _calculate_readability(self, text: str, words: List[str], sentences: List[str]) -> Dict[str, Any]:
        """Calculate readability scores"""
        if not words or not sentences:
            return {}
        
        # Flesch Reading Ease
        syllables = self._count_syllables(text)
        flesch_score = 206.835 - (1.015 * (len(words) / len(sentences))) - (84.6 * (syllables / len(words)))
        
        # Flesch-Kincaid Grade Level
        fk_grade = 0.39 * (len(words) / len(sentences)) + 11.8 * (syllables / len(words)) - 15.59
        
        return {
            'flesch_reading_ease': round(max(0, min(100, flesch_score)), 1),
            'flesch_kincaid_grade': round(max(0, fk_grade), 1),
            'readability_level': self._get_readability_level(flesch_score)
        }
    
    def _count_syllables(self, text: str) -> int:
        """Estimate syllable count"""
        text = text.lower()
        count = 0
        vowels = "aeiouy"
        on_vowel = False
        
        for char in text:
            is_vowel = char in vowels
            if is_vowel and not on_vowel:
                count += 1
            on_vowel = is_vowel
        
        return max(1, count)
    
    def _get_readability_level(self, score: float) -> str:
        """Get readability level description"""
        if score >= 90:
            return "Very Easy"
        elif score >= 80:
            return "Easy"
        elif score >= 70:
            return "Fairly Easy"
        elif score >= 60:
            return "Standard"
        elif score >= 50:
            return "Fairly Difficult"
        elif score >= 30:
            return "Difficult"
        else:
            return "Very Difficult"
    
    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze text sentiment"""
        # Simple rule-based sentiment analysis
        positive_words = {
            'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'awesome',
            'love', 'like', 'enjoy', 'happy', 'joy', 'success', 'win', 'best', 'perfect'
        }
        negative_words = {
            'bad', 'terrible', 'awful', 'horrible', 'worst', 'hate', 'dislike', 'sad',
            'angry', 'frustrated', 'fail', 'lose', 'problem', 'issue', 'error', 'broken'
        }
        
        words = self._tokenize(text.lower())
        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)
        total_words = len(words)
        
        if total_words == 0:
            return {'score': 0, 'label': 'neutral', 'confidence': 0}
        
        sentiment_score = (positive_count - negative_count) / total_words
        confidence = min(1.0, (positive_count + negative_count) / total_words * 2)
        
        if sentiment_score > 0.05:
            label = 'positive'
        elif sentiment_score < -0.05:
            label = 'negative'
        else:
            label = 'neutral'
        
        return {
            'score': round(sentiment_score, 3),
            'label': label,
            'confidence': round(confidence, 3),
            'positive_words': positive_count,
            'negative_words': negative_count
        }
    
    def _identify_topics(self, text: str) -> List[Dict[str, Any]]:
        """Identify topics in the text"""
        text_lower = text.lower()
        topics = []
        
        for topic, keywords in self.topic_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            if matches > 0:
                confidence = min(1.0, matches / len(keywords))
                topics.append({
                    'topic': topic,
                    'confidence': round(confidence, 3),
                    'keyword_matches': matches
                })
        
        # Sort by confidence
        topics.sort(key=lambda x: x['confidence'], reverse=True)
        return topics[:5]  # Return top 5 topics
    
    def _extract_keywords(self, words: List[str]) -> List[Dict[str, Any]]:
        """Extract important keywords"""
        if not words:
            return []
        
        word_freq = Counter(words)
        total_words = len(words)
        
        # Calculate TF-IDF like scores (simplified)
        keywords = []
        for word, freq in word_freq.most_common(20):
            if freq > 1:  # Only words that appear more than once
                import math
                importance = (freq / total_words) * math.log(total_words / freq)
                keywords.append({
                    'word': word,
                    'frequency': freq,
                    'importance': round(importance, 4)
                })
        
        return keywords[:10]  # Return top 10 keywords
    
    def _classify_content_type(self, text: str) -> Dict[str, Any]:
        """Classify the type of content"""
        text_lower = text.lower()
        
        # Check for different content types
        indicators = {
            'news': ['news', 'reports', 'announced', 'published', 'released'],
            'tutorial': ['how to', 'guide', 'tutorial', 'step by step', 'learn'],
            'review': ['review', 'rating', 'stars', 'recommend', 'opinion'],
            'technical': ['code', 'function', 'class', 'method', 'algorithm', 'api'],
            'marketing': ['buy', 'sale', 'discount', 'offer', 'promotion', 'subscribe'],
            'academic': ['research', 'study', 'analysis', 'data', 'results', 'conclusion']
        }
        
        scores = {}
        for content_type, keywords in indicators.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                scores[content_type] = score
        
        if scores:
            primary_type = max(scores, key=scores.get)
            confidence = min(1.0, scores[primary_type] / 3)
        else:
            primary_type = 'general'
            confidence = 0.5
        
        return {
            'primary_type': primary_type,
            'confidence': round(confidence, 3),
            'all_scores': scores
        }
    
    def _detect_language(self, text: str) -> Dict[str, Any]:
        """Simple language detection"""
        # This is a simplified version - in production, use a proper language detection library
        english_indicators = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of']
        spanish_indicators = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'no']
        
        words = self._tokenize(text.lower())
        english_count = sum(1 for word in words if word in english_indicators)
        spanish_count = sum(1 for word in words if word in spanish_indicators)
        
        if english_count > spanish_count:
            language = 'english'
            confidence = min(1.0, english_count / len(words) * 2)
        elif spanish_count > english_count:
            language = 'spanish'
            confidence = min(1.0, spanish_count / len(words) * 2)
        else:
            language = 'unknown'
            confidence = 0.5
        
        return {
            'detected_language': language,
            'confidence': round(confidence, 3)
        }
    
    def _calculate_duplicate_score(self, text: str) -> Dict[str, Any]:
        """Calculate duplicate content score"""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        if text_hash in self.content_cache:
            return {
                'is_duplicate': True,
                'duplicate_score': 1.0,
                'first_seen': self.content_cache[text_hash]
            }
        else:
            self.content_cache[text_hash] = datetime.utcnow().isoformat()
            return {
                'is_duplicate': False,
                'duplicate_score': 0.0,
                'first_seen': None
            }
    
    def _generate_summary(self, text: str, sentences: List[str]) -> Dict[str, Any]:
        """Generate text summary"""
        if not sentences:
            return {'summary': '', 'summary_length': 0}
        
        # Simple extractive summarization (select most important sentences)
        if len(sentences) <= 3:
            summary = ' '.join(sentences)
        else:
            # Select first, middle, and last sentences for summary
            summary_sentences = [
                sentences[0],
                sentences[len(sentences) // 2],
                sentences[-1]
            ]
            summary = ' '.join(summary_sentences)
        
        return {
            'summary': summary,
            'summary_length': len(summary),
            'compression_ratio': round(len(summary) / len(text), 3)
        }
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities (simplified)"""
        # Simple entity extraction using regex patterns
        entities = {
            'emails': re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text),
            'urls': re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text),
            'phone_numbers': re.findall(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text),
            'dates': re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text)
        }
        
        return {k: list(set(v)) for k, v in entities.items()}
    
    def _empty_analysis(self) -> Dict[str, Any]:
        """Return empty analysis structure"""
        return {
            'basic_stats': {},
            'readability': {},
            'sentiment': {'score': 0, 'label': 'neutral', 'confidence': 0},
            'topics': [],
            'keywords': [],
            'content_type': {'primary_type': 'unknown', 'confidence': 0},
            'language_detection': {'detected_language': 'unknown', 'confidence': 0},
            'duplicate_score': {'is_duplicate': False, 'duplicate_score': 0},
            'summary': {'summary': '', 'summary_length': 0},
            'entities': {},
            'metadata': {'analyzed_at': datetime.utcnow().isoformat()}
        }
    
    def analyze_multiple_pages(self, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze multiple pages and provide insights"""
        all_analyses = []
        all_text = ""
        all_links = []
        
        for page in pages:
            page_text = f"{page.get('title', '')} {' '.join(page.get('headings', []))} {' '.join(page.get('paragraphs', []))}"
            analysis = self.analyze_content(page_text)
            all_analyses.append(analysis)
            all_text += page_text + " "
            
            # Collect all links for recommendation analysis
            page_links = page.get('links', [])
            all_links.extend(page_links)
        
        # Aggregate insights
        combined_analysis = self.analyze_content(all_text)
        
        # Generate intelligent next website recommendations
        next_recommendations = self._generate_next_website_recommendations(
            combined_analysis, all_links, pages
        )
        
        return {
            'individual_analyses': all_analyses,
            'combined_analysis': combined_analysis,
            'cross_page_insights': self._generate_cross_page_insights(all_analyses, pages),
            'next_recommendations': next_recommendations
        }
    
    def _generate_cross_page_insights(self, analyses: List[Dict], pages: List[Dict]) -> Dict[str, Any]:
        """Generate insights across multiple pages"""
        if not analyses:
            return {}
        
        # Aggregate topics
        all_topics = {}
        for analysis in analyses:
            for topic in analysis.get('topics', []):
                topic_name = topic['topic']
                if topic_name not in all_topics:
                    all_topics[topic_name] = {'count': 0, 'total_confidence': 0}
                all_topics[topic_name]['count'] += 1
                all_topics[topic_name]['total_confidence'] += topic['confidence']
        
        # Calculate average sentiment
        sentiments = [a.get('sentiment', {}).get('score', 0) for a in analyses]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        
        # Find most common content types
        content_types = [a.get('content_type', {}).get('primary_type', 'unknown') for a in analyses]
        content_type_counts = Counter(content_types)
        
        return {
            'dominant_topics': sorted(all_topics.items(), key=lambda x: x[1]['count'], reverse=True)[:5],
            'average_sentiment': round(avg_sentiment, 3),
            'content_type_distribution': dict(content_type_counts.most_common()),
            'total_pages_analyzed': len(analyses)
        }
    
    def _generate_next_website_recommendations(self, analysis: Dict[str, Any], links: List[Dict], pages: List[Dict]) -> Dict[str, Any]:
        """Generate intelligent recommendations for next websites to scrape"""
        if not analysis or not links:
            return {'recommended_urls': [], 'reasoning': 'Insufficient data for recommendations'}
        
        # Extract key information from current analysis
        topics = analysis.get('topics', [])
        keywords = analysis.get('keywords', [])
        content_type = analysis.get('content_type', {}).get('primary_type', 'general')
        
        # Create keyword set for matching
        key_terms = set()
        if topics:
            key_terms.update([topic['topic'] for topic in topics[:3]])
        if keywords:
            key_terms.update([kw['word'] for kw in keywords[:10]])
        
        # Score and rank links
        scored_links = []
        seen_domains = set()
        
        for link in links:
            url = link.get('url', '')
            text = link.get('text', '').lower()
            
            if not url or not text:
                continue
            
            # Extract domain to avoid duplicates
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                if domain in seen_domains:
                    continue
                seen_domains.add(domain)
            except:
                continue
            
            # Calculate relevance score
            score = self._calculate_link_relevance_score(url, text, key_terms, content_type)
            
            if score > 0.1:  # Only include links with decent relevance
                scored_links.append({
                    'url': url,
                    'text': text,
                    'relevance_score': round(score, 3),
                    'reasoning': self._generate_link_reasoning(text, key_terms, content_type)
                })
        
        # Sort by relevance score and take top recommendations
        scored_links.sort(key=lambda x: x['relevance_score'], reverse=True)
        top_recommendations = scored_links[:5]
        
        # Generate learning path suggestions based on content type
        learning_path = self._suggest_learning_path(topics, content_type, keywords)
        
        # Generate search queries for discovering new content
        search_suggestions = self._generate_search_suggestions(topics, keywords, content_type)
        
        return {
            'recommended_urls': top_recommendations,
            'learning_path': learning_path,
            'search_suggestions': search_suggestions,
            'total_links_analyzed': len(links),
            'unique_domains_found': len(seen_domains),
            'recommendation_strategy': self._get_recommendation_strategy(content_type, topics)
        }
    
    def _calculate_link_relevance_score(self, url: str, text: str, key_terms: set, content_type: str) -> float:
        """Calculate how relevant a link is based on current content analysis"""
        score = 0.0
        text_lower = text.lower()
        url_lower = url.lower()
        
        # Keyword matching in link text (highest weight)
        for term in key_terms:
            if term in text_lower:
                score += 0.3
        
        # Keyword matching in URL
        for term in key_terms:
            if term in url_lower:
                score += 0.2
        
        # Content type specific scoring
        content_indicators = {
            'tutorial': ['tutorial', 'guide', 'how-to', 'learn', 'course', 'lesson'],
            'technical': ['documentation', 'docs', 'api', 'reference', 'spec', 'manual'],
            'news': ['news', 'article', 'blog', 'update', 'latest', 'recent'],
            'academic': ['research', 'paper', 'study', 'analysis', 'journal', 'academic'],
            'review': ['review', 'comparison', 'vs', 'evaluation', 'rating', 'opinion']
        }
        
        if content_type in content_indicators:
            for indicator in content_indicators[content_type]:
                if indicator in text_lower or indicator in url_lower:
                    score += 0.15
        
        # Boost educational content
        educational_terms = ['learn', 'tutorial', 'guide', 'course', 'education', 'training']
        for term in educational_terms:
            if term in text_lower:
                score += 0.1
        
        # Penalize low-quality indicators
        low_quality_terms = ['download', 'free', 'click', 'here', 'more', 'read more']
        for term in low_quality_terms:
            if term in text_lower:
                score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def _generate_link_reasoning(self, text: str, key_terms: set, content_type: str) -> str:
        """Generate human-readable reasoning for why a link was recommended"""
        reasons = []
        text_lower = text.lower()
        
        # Check for keyword matches
        matching_terms = [term for term in key_terms if term in text_lower]
        if matching_terms:
            reasons.append(f"Contains key topics: {', '.join(matching_terms[:3])}")
        
        # Check for content type alignment
        if content_type in ['tutorial', 'technical'] and any(word in text_lower for word in ['guide', 'tutorial', 'documentation']):
            reasons.append("Provides learning resources")
        elif content_type in ['news', 'article'] and any(word in text_lower for word in ['article', 'blog', 'news']):
            reasons.append("Related news/articles")
        elif any(word in text_lower for word in ['course', 'learn', 'education']):
            reasons.append("Educational content")
        
        if not reasons:
            reasons.append("Contextually related to current topic")
        
        return "; ".join(reasons)
    
    def _suggest_learning_path(self, topics: List[Dict], content_type: str, keywords: List[Dict]) -> List[Dict]:
        """Suggest a learning path based on current content"""
        learning_suggestions = []
        
        if topics:
            primary_topic = topics[0]['topic']
            
            # Define learning paths for different topics
            learning_paths = {
                'technology': [
                    {'step': 'Fundamentals', 'description': 'Learn basic concepts and terminology', 'search_terms': ['basics', 'introduction', 'fundamentals']},
                    {'step': 'Practical Examples', 'description': 'Find tutorials and hands-on guides', 'search_terms': ['tutorial', 'example', 'hands-on']},
                    {'step': 'Advanced Topics', 'description': 'Explore advanced concepts and best practices', 'search_terms': ['advanced', 'best practices', 'expert']},
                    {'step': 'Real-world Applications', 'description': 'See how it\'s used in production', 'search_terms': ['case study', 'production', 'real-world']}
                ],
                'business': [
                    {'step': 'Market Research', 'description': 'Understand the market landscape', 'search_terms': ['market research', 'industry analysis']},
                    {'step': 'Strategy Development', 'description': 'Learn strategic approaches', 'search_terms': ['strategy', 'planning', 'framework']},
                    {'step': 'Implementation', 'description': 'Find practical implementation guides', 'search_terms': ['implementation', 'execution', 'process']},
                    {'step': 'Case Studies', 'description': 'Study successful examples', 'search_terms': ['case study', 'success story', 'example']}
                ],
                'health': [
                    {'step': 'Basic Information', 'description': 'Understand fundamental health concepts', 'search_terms': ['basics', 'overview', 'introduction']},
                    {'step': 'Research & Studies', 'description': 'Find scientific research and studies', 'search_terms': ['research', 'study', 'clinical']},
                    {'step': 'Expert Opinions', 'description': 'Read expert analysis and opinions', 'search_terms': ['expert', 'doctor', 'professional']},
                    {'step': 'Practical Guidance', 'description': 'Find actionable health guidance', 'search_terms': ['guide', 'advice', 'recommendations']}
                ]
            }
            
            if primary_topic in learning_paths:
                learning_suggestions = learning_paths[primary_topic]
            else:
                # Generic learning path
                learning_suggestions = [
                    {'step': 'Foundation', 'description': 'Build foundational knowledge', 'search_terms': ['basics', 'introduction']},
                    {'step': 'Deep Dive', 'description': 'Explore topic in detail', 'search_terms': ['detailed', 'comprehensive']},
                    {'step': 'Advanced Concepts', 'description': 'Study advanced aspects', 'search_terms': ['advanced', 'expert level']},
                    {'step': 'Practical Application', 'description': 'Apply knowledge practically', 'search_terms': ['practical', 'application', 'examples']}
                ]
        
        return learning_suggestions
    
    def _generate_search_suggestions(self, topics: List[Dict], keywords: List[Dict], content_type: str) -> List[str]:
        """Generate search query suggestions for finding related content"""
        suggestions = []
        
        if topics and keywords:
            primary_topic = topics[0]['topic']
            top_keywords = [kw['word'] for kw in keywords[:5] if kw['frequency'] > 2]
            
            # Combine topics and keywords for search suggestions
            if top_keywords:
                suggestions.extend([
                    f"{primary_topic} {top_keywords[0]} tutorial",
                    f"{primary_topic} {top_keywords[0]} guide",
                    f"best {primary_topic} {top_keywords[0]} resources",
                    f"{primary_topic} {top_keywords[0]} examples",
                    f"learn {primary_topic} {top_keywords[0]}"
                ])
            
            # Add content-type specific suggestions
            if content_type == 'technical':
                suggestions.extend([
                    f"{primary_topic} documentation",
                    f"{primary_topic} API reference",
                    f"{primary_topic} best practices"
                ])
            elif content_type == 'tutorial':
                suggestions.extend([
                    f"{primary_topic} beginner guide",
                    f"{primary_topic} step by step",
                    f"{primary_topic} course"
                ])
            elif content_type == 'news':
                suggestions.extend([
                    f"{primary_topic} latest news",
                    f"{primary_topic} updates",
                    f"{primary_topic} trends"
                ])
        
        return suggestions[:8]  # Return top 8 suggestions
    
    def _get_recommendation_strategy(self, content_type: str, topics: List[Dict]) -> Dict[str, Any]:
        """Explain the recommendation strategy used"""
        strategy = {
            'approach': 'content-based filtering',
            'primary_factors': ['topic relevance', 'keyword matching', 'content type alignment'],
            'content_type': content_type
        }
        
        if topics:
            strategy['dominant_topic'] = topics[0]['topic']
            strategy['focus'] = f"Finding content related to {topics[0]['topic']}"
        else:
            strategy['focus'] = "General content discovery based on keywords"
        
        return strategy 