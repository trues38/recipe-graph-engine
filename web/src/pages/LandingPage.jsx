import React, { useState } from 'react';
import { ChefHat, Heart, Zap, ArrowRight, Sparkles, UtensilsCrossed } from 'lucide-react';
import { motion } from 'framer-motion';

const LandingPage = ({ onStart }) => {
  return (
    <div className="min-h-screen bg-slate-50 font-sans selection:bg-brand-200 selection:text-brand-900">
      {/* Navigation */}
      <nav className="fixed w-full z-50 bg-white/80 backdrop-blur-md border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-brand-400 to-brand-600 rounded-lg flex items-center justify-center text-white shadow-lg">
                <ChefHat size={20} />
              </div>
              <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-800 to-slate-600">
                Recipe AI
              </span>
            </div>
            <button 
              onClick={onStart}
              className="text-sm font-medium text-slate-600 hover:text-brand-600 transition-colors"
            >
              Launch App
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 lg:pt-48 lg:pb-32 overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full max-w-7xl pointer-events-none">
          <div className="absolute top-20 right-0 w-[500px] h-[500px] bg-brand-200/30 rounded-full blur-3xl" />
          <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-purple-200/30 rounded-full blur-3xl" />
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
          <div className="text-center max-w-4xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-50 border border-brand-100 text-brand-700 text-sm font-medium mb-8">
                <Sparkles size={14} />
                <span>Powered by Neo4j Graph Technology</span>
              </div>
              <h1 className="text-5xl lg:text-7xl font-bold tracking-tight text-slate-900 mb-8">
                Turn Your Ingredients into <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-500 to-amber-500">
                  Culinary Masterpieces
                </span>
              </h1>
              <p className="text-xl text-slate-600 mb-10 max-w-2xl mx-auto leading-relaxed">
                Not just a search engine. A smart culinary companion that understands your ingredients, health goals, and taste preferences.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <button 
                  onClick={onStart}
                  className="w-full sm:w-auto px-8 py-4 bg-brand-600 hover:bg-brand-700 text-white rounded-xl font-semibold shadow-lg shadow-brand-500/20 flex items-center justify-center gap-2 transition-all transform hover:-translate-y-0.5"
                >
                  Start Cooking Now
                  <ArrowRight size={20} />
                </button>
                <button className="w-full sm:w-auto px-8 py-4 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 rounded-xl font-semibold transition-colors">
                  View Features
                </button>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 bg-white relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-slate-900 mb-4">Why Recipe AI?</h2>
            <p className="text-slate-600 max-w-2xl mx-auto">
              We move beyond simple keyword matching. Our graph engine understands the relationships between ingredients, flavors, and nutrition.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <FeatureCard 
              icon={<UtensilsCrossed />}
              title="Smart Ingredient Match"
              description="Have 3 eggs and a tomato? We'll find recipes that maximize what you have and minimize what you need to buy."
              color="bg-orange-100 text-orange-600"
            />
            <FeatureCard 
              icon={<Heart />}
              title="Health & Diet Focused"
              description="Diabetes-friendly? High protein for bulking? Vegan? Our engine filters recipes based on your specific health conditions."
              color="bg-red-100 text-red-600"
            />
            <FeatureCard 
              icon={<Zap />}
              title="Persona-Based Chef"
              description="Talk to 'Mom' for warm home cooking advice, or a 'Diet Coach' for strict calorie counting. Different tones for different needs."
              color="bg-purple-100 text-purple-600"
            />
          </div>
        </div>
      </section>
    </div>
  );
};

const FeatureCard = ({ icon, title, description, color }) => (
  <div className="p-8 rounded-2xl bg-slate-50 border border-slate-100 hover:border-brand-200 transition-colors group">
    <div className={`w-12 h-12 rounded-xl ${color} flex items-center justify-center mb-6 group-hover:scale-110 transition-transform`}>
      {icon}
    </div>
    <h3 className="text-xl font-semibold text-slate-900 mb-3">{title}</h3>
    <p className="text-slate-600 leading-relaxed">
      {description}
    </p>
  </div>
);

export default LandingPage;
