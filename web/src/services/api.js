export const PERSONAS = [
  {
    id: 'UMMA',
    name: "Mother's Touch",
    icon: "👩‍🍳",
    description: "Warm, home-style advice",
    color: "bg-orange-100 text-orange-600 border-orange-200"
  },
  {
    id: 'QUICK',
    name: "Student Quick",
    icon: "⚡",
    description: "Fast, simple (under 20m)",
    color: "bg-yellow-100 text-yellow-600 border-yellow-200"
  },
  {
    id: 'DIET',
    name: "Diet Coach",
    icon: "💪",
    description: "Calorie & Protein focused",
    color: "bg-green-100 text-green-600 border-green-200"
  },
  {
    id: 'CHEF',
    name: "Master Chef",
    icon: "🖤",
    description: "Premium & Technique driven",
    color: "bg-slate-800 text-white border-slate-900"
  }
];

export const MOCKED_RECIPES = [
  {
    id: 1,
    name: "Kimchi Stew (Kimchi-jjigae)",
    category: "Stew",
    time: 30,
    difficulty: "Easy",
    calories: 520,
    protein: 38,
    match: 85,
    missing: ["Tofu"],
    image: "🥘"
  },
  {
    id: 2,
    name: "Spicy Pork Stir-fry",
    category: "Main Dish",
    time: 25,
    difficulty: "Medium",
    calories: 640,
    protein: 45,
    match: 100,
    missing: [],
    image: "🍖"
  },
  {
    id: 3,
    name: "Kimchi Fried Rice",
    category: "Rice",
    time: 15,
    difficulty: "Easy",
    calories: 480,
    protein: 12,
    match: 90,
    missing: [],
    image: "🍚"
  }
];

export const getPersonaMessage = (personaId, ingredients) => {
  const count = ingredients.length;
  switch (personaId) {
    case 'UMMA':
      return `Oh my, you have ${count} ingredients! Why don't you make a warm Kimchi Stew today? It's chilly outside!`;
    case 'QUICK':
      return `Yo, ${count} items? Easy. Kimchi Fried Rice takes literally 10 mins. Just fry it up.`;
    case 'DIET':
      return `Good selection. You can hit 38g of protein with the Stew, but watch the sodium! Maybe skip the extra broth.`;
    case 'CHEF':
      return `With these ingredients, the optimal flavor profile would be achieved by aging the Kimchi slightly more before sautéing.`;
    default:
      return "Here are some recommendations for you.";
  }
};

// Use Vercel API proxy for HTTPS
const API_URL = '/api';

// 카테고리 목록
export const CATEGORIES = [
  { id: "국/찌개", name: "국/찌개", icon: "🍲" },
  { id: "메인요리", name: "메인요리", icon: "🍖" },
  { id: "반찬", name: "반찬", icon: "🥗" },
  { id: "밑반찬", name: "밑반찬", icon: "🫙" },
  { id: "간식", name: "간식", icon: "🍰" },
];

// 카테고리 기반 레시피 검색 (신규)
export const searchByCategory = async (category, ingredients = [], personaId = 'UMMA') => {
  try {
    const response = await fetch(`${API_URL}/recommend/category`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        category: category,
        ingredients: ingredients,
        persona: getModeName(personaId),
        limit: 10
      })
    });

    if (!response.ok) {
      throw new Error('API request failed');
    }

    const data = await response.json();

    return {
      message: data.message,
      recipes: data.recipes.map(r => ({
        id: r.name,
        name: r.name,
        category: r.category || category,
        time: r.cooking_time || 30,
        difficulty: r.difficulty || '보통',
        calories: r.calories || 0,
        matchedCount: r.matched_count || 0,
        matchedIngredients: r.matched_ingredients || [],
        missingIngredients: r.missing_ingredients || [],
        totalIngredients: r.total_ingredients || 0,
        image: getCategoryEmoji(r.category),
        trending: r.trending || false,
        xLikes: r.x_likes || 0,
        xTip: r.x_tip || null
      })),
      category: data.category,
      inputIngredients: data.input_ingredients,
      persona: data.persona
    };
  } catch (error) {
    console.error('API error:', error);
    return {
      message: `${category} 레시피를 불러오는 중 오류가 발생했어요.`,
      recipes: [],
      category: category,
      inputIngredients: ingredients
    };
  }
};

// 기존 검색 (호환성 유지)
export const searchRecipes = async (ingredients, personaId) => {
  // 기본 카테고리로 검색
  return searchByCategory("메인요리", ingredients, personaId);
};

const getModeName = (personaId) => {
  const modeMap = {
    'UMMA': '엄마밥',
    'QUICK': '자취생',
    'DIET': '다이어트',
    'CHEF': '흑백요리사',
    'HEALTH': '건강맞춤',
    'VEGAN': '비건'
  };
  return modeMap[personaId] || '엄마밥';
};

const getCategoryEmoji = (category) => {
  const emojiMap = {
    '찌개': '🥘',
    '볶음': '🍳',
    '국': '🍲',
    '밥': '🍚',
    '면': '🍜',
    '구이': '🍖',
    '샐러드': '🥗'
  };
  return emojiMap[category] || '🍽️';
};

// 레시피 상세 정보 조회
export const getRecipeDetail = async (recipeName) => {
  try {
    const response = await fetch(`${API_URL}/recipe/${encodeURIComponent(recipeName)}`);
    if (!response.ok) {
      throw new Error('Recipe not found');
    }
    return await response.json();
  } catch (error) {
    return null;
  }
};

// 채팅 API 호출
export const sendChat = async (message) => {
  try {
    const response = await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: message,
        user_name: 'User' 
      })
    });

    if (!response.ok) {
      throw new Error('Chat API failed');
    }

    return await response.json();
  } catch (error) {
    console.error('Chat error:', error);
    throw error;
  }
};
