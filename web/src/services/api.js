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

export const searchRecipes = async (ingredients, personaId) => {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 800));
  
  return {
    message: getPersonaMessage(personaId, ingredients),
    recipes: MOCKED_RECIPES
  };
};
