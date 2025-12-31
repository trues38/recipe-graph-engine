import React, { useState, useRef, useEffect } from "react";
import {
  MessageCircle,
  Send,
  X,
  ChefHat,
  Sparkles,
  User,
  Minimize2,
  Maximize2,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { sendChat } from "../services/api";

const ChatWidget = () => {
  const [isOpen, setIsOpen] = useState(false); // Start closed
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: '안녕하세요! 맛있는 레시피를 찾아드릴까요? 냉장고에 있는 재료를 알려주시거나, "한국요리 기본 추천해줘"라고 물어보세요!',
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isOpen]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = inputValue.trim();
    setInputValue("");
    setMessages((prev) => [...prev, { role: "user", text: userMessage }]);
    setIsLoading(true);

    try {
      const response = await sendChat(userMessage); // Call API

      // Add bot response
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: response.reply,
          recipes: response.recipes,
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "죄송합니다. 잠시 문제가 발생했어요. 다시 시도해주세요.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      {/* Floating Toggle Button */}
      <motion.button
        className="fixed bottom-6 right-6 w-14 h-14 bg-gradient-to-tr from-brand-600 to-brand-400 text-white rounded-full shadow-lg flex items-center justify-center z-50 hover:shadow-xl hover:scale-105 transition-all"
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        onClick={() => setIsOpen(!isOpen)}
      >
        {isOpen ? <X size={24} /> : <MessageCircle size={28} />}
        {!isOpen && (
          <span className="absolute -top-1 -right-1 flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
          </span>
        )}
      </motion.button>

      {/* Chat Window */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 50, scale: 0.9 }}
            className="fixed bottom-24 right-6 w-[360px] md:w-[400px] h-[600px] max-h-[80vh] bg-white/90 dark:bg-slate-800/90 backdrop-blur-xl border border-white/20 dark:border-slate-700 rounded-3xl shadow-2xl z-50 flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="p-4 bg-gradient-to-r from-brand-600/90 to-brand-500/90 backdrop-blur-md text-white flex justify-between items-center shadow-md">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-sm">
                  <ChefHat size={20} className="text-white" />
                </div>
                <div>
                  <h3 className="font-bold text-sm">Recipe AI Chef</h3>
                  <div className="flex items-center gap-1 text-xs opacity-80">
                    <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                    Online
                  </div>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="opacity-70 hover:opacity-100"
              >
                <Minimize2 size={18} />
              </button>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-slate-200 dark:scrollbar-thumb-slate-700">
              {messages.map((msg, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex ${
                    msg.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[85%] p-3 rounded-2xl text-sm leading-relaxed shadow-sm ${
                      msg.role === "user"
                        ? "bg-brand-500 text-white rounded-tr-none"
                        : "bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 rounded-tl-none border border-slate-100 dark:border-slate-600"
                    }`}
                  >
                    {msg.text}

                    {/* Embedded Recipes Preview */}
                    {msg.recipes && msg.recipes.length > 0 && (
                      <div className="mt-3 space-y-2">
                        {msg.recipes.slice(0, 3).map((recipe, rIdx) => (
                          <div
                            key={rIdx}
                            className="bg-slate-50 dark:bg-slate-800/50 p-2 rounded-lg border border-slate-100 dark:border-slate-600 flex items-center gap-2 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                          >
                            <div className="w-8 h-8 bg-brand-100 dark:bg-brand-900/30 text-brand-600 rounded-md flex items-center justify-center text-xs">
                              🍳
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="font-semibold text-xs truncate dark:text-slate-200">
                                {recipe.name}
                              </div>
                              <div className="text-[10px] text-slate-500">
                                {recipe.calories}kcal • {recipe.matched}개 매칭
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
              {isLoading && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex justify-start"
                >
                  <div className="bg-white dark:bg-slate-700 p-3 rounded-2xl rounded-tl-none border border-slate-100 dark:border-slate-600 flex gap-1">
                    <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce"></span>
                    <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce delay-75"></span>
                    <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce delay-150"></span>
                  </div>
                </motion.div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 bg-white/50 dark:bg-slate-800/50 backdrop-blur-sm border-t border-slate-100 dark:border-slate-700">
              <div className="flex items-center gap-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-600 rounded-full px-4 py-2 focus-within:ring-2 focus-within:ring-brand-500/50 transition-all shadow-sm">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="메시지를 입력세요..."
                  className="flex-1 bg-transparent border-none outline-none text-sm dark:text-white placeholder:text-slate-400"
                  disabled={isLoading}
                />
                <button
                  onClick={handleSend}
                  disabled={!inputValue.trim() || isLoading}
                  className="p-1.5 rounded-full bg-brand-500 text-white disabled:bg-slate-300 dark:disabled:bg-slate-600 transition-colors hover:bg-brand-600"
                >
                  <Send size={14} />
                </button>
              </div>
              <div className="text-[10px] text-center text-slate-400 mt-2">
                Recipe AI can make mistakes. Check important info.
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default ChatWidget;
