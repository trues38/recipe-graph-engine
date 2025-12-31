import React, { useState } from 'react';
import { Search, ArrowLeft, Plus, X, ChefHat, Sparkles, Clock, Flame, Info } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { PERSONAS, searchRecipes } from '../services/api';

const AppPage = ({ onBack }) => {
  const [ingredients, setIngredients] = useState(['Kimchi', 'Pork', 'Onion']);
  const [inputValue, setInputValue] = useState('');
  const [selectedPersona, setSelectedPersona] = useState(PERSONAS[0]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleAddIngredient = (e) => {
    if (e.key === 'Enter' && inputValue.trim()) {
      setIngredients([...ingredients, inputValue.trim()]);
      setInputValue('');
    }
  };

  const removeIngredient = (index) => {
    setIngredients(ingredients.filter((_, i) => i !== index));
  };

  const handleSearch = async () => {
    setLoading(true);
    try {
      const data = await searchRecipes(ingredients, selectedPersona.id);
      setResult(data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col md:flex-row">
      
      {/* Sidebar - Persona Selector */}
      <aside className="w-full md:w-80 bg-white border-r border-slate-200 p-6 flex flex-col h-auto md:h-screen sticky top-0 z-10">
        <div className="flex items-center gap-2 mb-8 cursor-pointer" onClick={onBack}>
          <div className="w-8 h-8 bg-brand-500 rounded-lg flex items-center justify-center text-white">
            <ChefHat size={18} />
          </div>
          <span className="font-bold text-lg text-slate-800">Recipe AI</span>
        </div>

        <div className="mb-6">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">Choose Your Chef</h3>
          <div className="space-y-3">
            {PERSONAS.map(persona => (
              <button
                key={persona.id}
                onClick={() => setSelectedPersona(persona)}
                className={`w-full text-left p-3 rounded-xl border transition-all ${
                  selectedPersona.id === persona.id
                    ? `${persona.color} shadow-sm ring-1 ring-offset-1 ring-transparent`
                    : 'bg-white border-slate-100 text-slate-600 hover:bg-slate-50 hover:border-slate-200'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{persona.icon}</span>
                  <div>
                    <div className="font-semibold text-sm">{persona.name}</div>
                    <div className="text-xs opacity-80">{persona.description}</div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-4 md:p-8 overflow-y-auto">
        <div className="max-w-4xl mx-auto">
          
          {/* Input Section */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 mb-8">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">What's in your fridge?</h2>
            <div className="flex flex-wrap gap-2 mb-4">
              {ingredients.map((ing, i) => (
                <span key={i} className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-slate-100 text-slate-700 text-sm font-medium">
                  {ing}
                  <button onClick={() => removeIngredient(i)} className="hover:text-red-500"><X size={14}/></button>
                </span>
              ))}
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleAddIngredient}
                placeholder="Add ingredient + Enter"
                className="bg-transparent outline-none text-sm min-w-[120px] placeholder:text-slate-400"
              />
            </div>
            
            <div className="flex justify-between items-center pt-4 border-t border-slate-100">
               <div className="text-sm text-slate-500 flex items-center gap-1">
                 <Info size={14} />
                 <span>Press Enter to add tags</span>
               </div>
               <button 
                onClick={handleSearch}
                disabled={loading}
                className="bg-brand-600 hover:bg-brand-700 text-white px-6 py-2.5 rounded-xl font-medium shadow-lg shadow-brand-500/20 flex items-center gap-2 disabled:opacity-70 transition-all"
               >
                 {loading ? <Sparkles className="animate-spin" size={18} /> : <Search size={18} />}
                 {loading ? 'Cooking...' : 'Find Recipes'}
               </button>
            </div>
          </div>

          {/* Results Area */}
          <AnimatePresence mode='wait'>
            {result && (
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
              >
                {/* Persona Message */}
                <div className={`p-6 rounded-2xl mb-8 flex gap-4 ${selectedPersona.color.split(' ')[0]} bg-opacity-20 border border-current border-opacity-10`}>
                  <div className="text-4xl">{selectedPersona.icon}</div>
                  <div>
                    <h3 className="font-bold text-lg mb-1">{selectedPersona.name} says...</h3>
                    <p className="leading-relaxed opacity-90">{result.message}</p>
                  </div>
                </div>

                {/* Recipe Grid */}
                <div className="grid md:grid-cols-2 gap-6">
                  {result.recipes.map(recipe => (
                    <div key={recipe.id} className="bg-white rounded-2xl border border-slate-100 overflow-hidden hover:shadow-md transition-shadow group">
                      <div className="h-48 bg-slate-100 flex items-center justify-center text-6xl relative">
                         {recipe.image}
                         <div className="absolute top-3 right-3 bg-white/90 backdrop-blur px-2 py-1 rounded-lg text-xs font-bold text-slate-800 shadow-sm">
                           {recipe.match}% Match
                         </div>
                      </div>
                      <div className="p-5">
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <span className="text-xs font-bold text-brand-600 uppercase tracking-wide">{recipe.category}</span>
                            <h3 className="font-bold text-slate-900 text-lg group-hover:text-brand-600 transition-colors">{recipe.name}</h3>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-4 text-sm text-slate-500 mb-4">
                          <div className="flex items-center gap-1"><Clock size={14}/> {recipe.time}m</div>
                          <div className="flex items-center gap-1"><Flame size={14}/> {recipe.calories} kcal</div>
                        </div>

                        {recipe.missing.length > 0 ? (
                           <div className="text-sm text-slate-500 bg-slate-50 p-3 rounded-lg">
                             <span className="font-medium text-slate-700">Missing:</span> {recipe.missing.join(', ')}
                           </div>
                        ) : (
                          <div className="text-sm text-green-600 bg-green-50 p-3 rounded-lg flex items-center gap-2">
                             <Sparkles size={14} /> You have all ingredients!
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          
          {!result && !loading && (
            <div className="text-center py-20 opacity-30">
              <ChefHat size={48} className="mx-auto mb-4" />
              <p className="text-xl font-medium">Ready to cook something delicious?</p>
            </div>
          )}

        </div>
      </main>
    </div>
  );
};

export default AppPage;
