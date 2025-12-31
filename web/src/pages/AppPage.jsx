import React, { useState, useEffect } from 'react';
import { Search, ArrowLeft, Plus, X, ChefHat, Sparkles, Clock, Flame, Info, Globe, Moon, Sun } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { PERSONAS, CATEGORIES, searchByCategory } from '../services/api';
import { useLanguage } from '../contexts/LanguageContext';
import { useTheme } from '../contexts/ThemeContext';

const AppPage = ({ onBack }) => {
  const [ingredients, setIngredients] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [selectedPersona, setSelectedPersona] = useState(PERSONAS[0]);
  const [selectedCategory, setSelectedCategory] = useState(CATEGORIES[0]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const { t, language, toggleLanguage } = useLanguage();
  const { theme, toggleTheme } = useTheme();

  // 카테고리 변경시 자동 검색
  useEffect(() => {
    handleSearch();
  }, [selectedCategory]);

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
      const data = await searchByCategory(selectedCategory.id, ingredients, selectedPersona.id);
      setResult(data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex flex-col md:flex-row transition-colors duration-300">
      
      {/* Sidebar - Persona Selector */}
      <aside className="w-full md:w-80 bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 p-6 flex flex-col h-auto md:h-screen sticky top-0 z-10 transition-colors duration-300">
        <div className="flex justify-between items-center mb-8">
            <div className="flex items-center gap-2 cursor-pointer" onClick={onBack}>
              <div className="w-8 h-8 bg-brand-500 rounded-lg flex items-center justify-center text-white">
                <ChefHat size={18} />
              </div>
              <span className="font-bold text-lg text-slate-800 dark:text-white">Recipe AI</span>
            </div>
            
            <div className="flex gap-2">
                 <button onClick={toggleLanguage} className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-400">
                   <Globe size={16} />
                 </button>
                 <button onClick={toggleTheme} className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-400">
                   {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
                 </button>
            </div>
        </div>

        <div className="mb-6">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">{t('app.sidebar.title')}</h3>
          <div className="space-y-3">
            {PERSONAS.map(persona => (
              <button
                key={persona.id}
                onClick={() => setSelectedPersona(persona)}
                className={`w-full text-left p-3 rounded-xl border transition-all ${
                  selectedPersona.id === persona.id
                    ? `${persona.color} shadow-sm ring-1 ring-offset-1 ring-transparent`
                    : 'bg-white dark:bg-slate-800 border-slate-100 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700 hover:border-slate-200'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{persona.icon}</span>
                  <div>
                    <div className="font-semibold text-sm">{t(`persona.${persona.id}.name`)}</div>
                    <div className="text-xs opacity-80">{t(`persona.${persona.id}.desc`)}</div>
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
          
          {/* Category Selector */}
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 p-4 mb-4 transition-colors duration-300">
            <div className="flex gap-2 overflow-x-auto pb-2">
              {CATEGORIES.map(cat => (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(cat)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl whitespace-nowrap transition-all ${
                    selectedCategory.id === cat.id
                      ? 'bg-brand-600 text-white shadow-lg'
                      : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'
                  }`}
                >
                  <span className="text-xl">{cat.icon}</span>
                  <span className="font-medium">{cat.name}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Input Section */}
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-sm border border-slate-100 dark:border-slate-700 p-6 mb-8 transition-colors duration-300">
            <h2 className="text-lg font-semibold text-slate-800 dark:text-white mb-4">재료 입력 (선택)</h2>
            <div className="flex flex-wrap gap-2 mb-4">
              {ingredients.map((ing, i) => (
                <span key={i} className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 text-sm font-medium">
                  {ing}
                  <button onClick={() => removeIngredient(i)} className="hover:text-red-500"><X size={14}/></button>
                </span>
              ))}
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleAddIngredient}
                placeholder={t('app.input.placeholder')}
                className="bg-transparent outline-none text-sm min-w-[120px] placeholder:text-slate-400 dark:placeholder:text-slate-500 dark:text-white"
              />
            </div>
            
            <div className="flex justify-between items-center pt-4 border-t border-slate-100 dark:border-slate-700">
               <div className="text-sm text-slate-500 dark:text-slate-400 flex items-center gap-1">
                 <Info size={14} />
                 <span>재료를 입력하면 매칭되는 레시피가 상위에 표시됩니다</span>
               </div>
               <button
                onClick={handleSearch}
                disabled={loading}
                className="bg-brand-600 hover:bg-brand-700 text-white px-6 py-2.5 rounded-xl font-medium shadow-lg shadow-brand-500/20 flex items-center gap-2 disabled:opacity-70 transition-all"
               >
                 {loading ? <Sparkles className="animate-spin" size={18} /> : <Search size={18} />}
                 {loading ? '검색 중...' : '레시피 찾기'}
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
                <div className={`p-6 rounded-2xl mb-8 flex gap-4 ${selectedPersona.color.split(' ')[0]} bg-opacity-20 border border-current border-opacity-10 dark:bg-opacity-10`}>
                  <div className="text-4xl">{selectedPersona.icon}</div>
                  <div>
                    <h3 className="font-bold text-lg mb-1 dark:text-white">{t(`persona.${selectedPersona.id}.name`)} says...</h3>
                    <p className="leading-relaxed opacity-90 dark:text-slate-200">{result.message}</p>
                  </div>
                </div>

                {/* Recipe Grid */}
                <div className="grid md:grid-cols-2 gap-6">
                  {result.recipes.map(recipe => (
                    <div key={recipe.id} className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 overflow-hidden hover:shadow-md dark:hover:shadow-slate-700/50 transition-all group">
                      <div className="h-32 bg-slate-100 dark:bg-slate-700 flex items-center justify-center text-5xl relative">
                         {recipe.image}
                         {recipe.matchedCount > 0 && (
                           <div className="absolute top-3 right-3 bg-green-500 text-white px-2 py-1 rounded-lg text-xs font-bold shadow-sm">
                             {recipe.matchedCount}개 매칭
                           </div>
                         )}
                      </div>
                      <div className="p-5">
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <span className="text-xs font-bold text-brand-600 dark:text-brand-400 uppercase tracking-wide">{recipe.category}</span>
                            <h3 className="font-bold text-slate-900 dark:text-white text-lg group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">{recipe.name}</h3>
                          </div>
                        </div>

                        <div className="flex items-center gap-4 text-sm text-slate-500 dark:text-slate-400 mb-3">
                          <div className="flex items-center gap-1"><Clock size={14}/> {recipe.time || '?'}분</div>
                          <div className="flex items-center gap-1">재료 {recipe.totalIngredients}개</div>
                        </div>

                        {recipe.matchedIngredients && recipe.matchedIngredients.length > 0 && (
                          <div className="text-sm text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 p-2 rounded-lg mb-2">
                            <span className="font-medium">✓ 있는 재료:</span> {recipe.matchedIngredients.join(', ')}
                          </div>
                        )}

                        {recipe.missingIngredients && recipe.missingIngredients.length > 0 && (
                          <div className="text-sm text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-700/50 p-2 rounded-lg">
                            <span className="font-medium text-slate-700 dark:text-slate-300">+ 필요:</span> {recipe.missingIngredients.slice(0, 3).join(', ')}{recipe.missingIngredients.length > 3 ? ` 외 ${recipe.missingIngredients.length - 3}개` : ''}
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
            <div className="text-center py-20 opacity-30 dark:opacity-20 text-slate-900 dark:text-white">
              <ChefHat size={48} className="mx-auto mb-4" />
              <p className="text-xl font-medium">{t('app.empty.ready')}</p>
            </div>
          )}

        </div>
      </main>
    </div>
  );
};

export default AppPage;
