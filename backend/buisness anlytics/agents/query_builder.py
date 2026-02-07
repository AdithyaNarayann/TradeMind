"""
AGENT 1: Query Builder Agent
Purpose: Convert seller input into optimized Amazon search query
Type: Semi-AI (rule-based with optional LLM enhancement)
"""
import re
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class QueryBuilderAgent:
    """
    Builds optimized Amazon search queries from product details
    """
    
    # Common noise words to remove
    NOISE_WORDS = {
        'the', 'a', 'an', 'for', 'with', 'and', 'or', 'but',
        'in', 'on', 'at', 'to', 'from', 'of', 'by'
    }
    
    # Priority keywords that should always be kept
    PRIORITY_KEYWORDS = {
        'wireless', 'bluetooth', 'noise', 'cancellation', 'pro',
        'plus', 'max', 'mini', 'air', 'ultra', 'premium'
    }
    
    def __init__(self, use_llm: bool = False, llm_client = None):
        """
        Args:
            use_llm: Whether to use LLM for advanced query optimization
            llm_client: OpenAI client if use_llm is True
        """
        self.use_llm = use_llm
        self.llm_client = llm_client
    
    def build_query(
        self,
        product_name: str,
        category: str,
        specs: List[str]
    ) -> str:
        """
        Build optimized search query
        
        Args:
            product_name: Product name from seller
            category: Product category
            specs: List of specifications
            
        Returns:
            Optimized search query string
        """
        try:
            # Step 1: Clean and tokenize product name
            cleaned_name = self._clean_product_name(product_name)
            
            # Step 2: Extract key specs
            key_specs = self._extract_key_specs(specs)
            
            # Step 3: Combine intelligently
            query_parts = [cleaned_name] + key_specs
            base_query = ' '.join(query_parts)
            
            # Step 4: Optional LLM enhancement
            if self.use_llm and self.llm_client:
                base_query = self._enhance_with_llm(base_query, category)
            
            # Step 5: Final cleanup
            final_query = self._final_cleanup(base_query)
            
            logger.info(f"Built query: '{final_query}' from '{product_name}'")
            return final_query
            
        except Exception as e:
            logger.error(f"Query building failed: {e}")
            # Fallback: return cleaned product name
            return self._clean_product_name(product_name)
    
    def _clean_product_name(self, name: str) -> str:
        """Remove noise and normalize product name"""
        # Convert to lowercase
        name = name.lower().strip()
        
        # Remove special characters except spaces and hyphens
        name = re.sub(r'[^\w\s-]', ' ', name)
        
        # Split into words
        words = name.split()
        
        # Remove noise words but keep priority keywords
        cleaned_words = []
        for word in words:
            word = word.strip()
            if not word:
                continue
            # Keep if priority keyword or not noise word
            if word in self.PRIORITY_KEYWORDS or word not in self.NOISE_WORDS:
                cleaned_words.append(word)
        
        return ' '.join(cleaned_words)
    
    def _extract_key_specs(self, specs: List[str], max_specs: int = 3) -> List[str]:
        """Extract most important specs for search"""
        if not specs:
            return []
        
        key_specs = []
        
        for spec in specs[:max_specs]:
            # Clean spec
            spec = spec.lower().strip()
            
            # Extract meaningful parts
            # Example: "Bluetooth 5.3" -> "bluetooth 5.3"
            spec = re.sub(r'[^\w\s.]', ' ', spec)
            
            # Keep if it has substance
            if len(spec) > 2:
                key_specs.append(spec)
        
        return key_specs
    
    def _enhance_with_llm(self, base_query: str, category: str) -> str:
        """
        Use LLM to optimize query for Amazon search
        This is optional and can improve results
        """
        try:
            prompt = f"""You are an Amazon search query optimizer.

Given this product search query: "{base_query}"
Category: {category}

Generate the most effective Amazon search query. Rules:
1. Keep it concise (3-6 words)
2. Use words customers actually search for
3. Include key differentiators
4. Remove redundancy
5. Prioritize popular terms

Output ONLY the optimized query, nothing else."""

            response = self.llm_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=50
            )
            
            optimized = response.choices[0].message.content.strip()
            
            # Validate it's reasonable
            if 2 <= len(optimized.split()) <= 10:
                return optimized
            else:
                return base_query
                
        except Exception as e:
            logger.warning(f"LLM enhancement failed: {e}, using base query")
            return base_query
    
    def _final_cleanup(self, query: str) -> str:
        """Final normalization"""
        # Remove extra spaces
        query = ' '.join(query.split())
        
        # Trim to reasonable length
        words = query.split()
        if len(words) > 8:
            words = words[:8]
        
        return ' '.join(words).strip()
    
    def validate_query(self, query: str) -> bool:
        """
        Check if query is valid
        
        Returns:
            True if query is good enough to use
        """
        if not query or len(query) < 3:
            return False
        
        # Should have at least 2 words for better results
        if len(query.split()) < 2:
            return False
        
        return True


# ===== USAGE EXAMPLE =====
if __name__ == "__main__":
    # Test without LLM
    agent = QueryBuilderAgent(use_llm=False)
    
    test_cases = [
        {
            "product_name": "Boat wireless earbuds",
            "category": "Electronics",
            "specs": ["Bluetooth 5.3", "Noise Cancellation", "IPX7"]
        },
        {
            "product_name": "Samsung Galaxy S24 Ultra 5G",
            "category": "Smartphones",
            "specs": ["256GB", "12GB RAM", "200MP Camera"]
        }
    ]
    
    for test in test_cases:
        query = agent.build_query(
            test["product_name"],
            test["category"],
            test["specs"]
        )
        print(f"Input: {test['product_name']}")
        print(f"Query: {query}")
        print(f"Valid: {agent.validate_query(query)}")
        print("-" * 50)
