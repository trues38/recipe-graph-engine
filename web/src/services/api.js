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

const API_URL = import.meta.env.VITE_API_URL || 'http://141.164.35.214:8002';

export const searchRecipes = async (ingredients, personaId) => {
  try {
    const response = await fetch(`${API_URL}/recommend/mode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mode: getModeName(personaId),
        ingredients: ingredients,
        limit: 10
      })
    });

    if (!response.ok) {
      throw new Error('API request failed');
    }

    const data = await response.json();

    return {
      message: data.message || getPersonaMessage(personaId, ingredients),
      recipes: data.recipes.map(r => ({
        id: r.name,
        name: r.name,
        category: r.category || 'Main',
        time: r.time_minutes || 30,
        difficulty: r.difficulty || 'Medium',
        calories: r.calories || 0,
        protein: r.protein || 0,
        match: r.coverage || 0,
        missing: [],
        image: getCategoryEmoji(r.category)
      }))
    };
  } catch (error) {
    console.error('API error:', error);
    // Fallback to mock data
    return {
      message: getPersonaMessage(personaId, ingredients),
      recipes: MOCKED_RECIPES
    };
  }
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
