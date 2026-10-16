import React from "react";
import { Sparkles, History, Landmark, Gem } from "lucide-react";
import { SUGGESTED_QUESTIONS, SuggestedQuestion, UI_STRINGS } from "@/theme/tokens";

interface SuggestedQuestionsProps {
  language: "kn" | "en";
  onSelectQuestion: (questionText: string) => void;
}

export const SuggestedQuestions: React.FC<SuggestedQuestionsProps> = ({
  language,
  onSelectQuestion,
}) => {
  const t = UI_STRINGS[language];

  const getCategoryIcon = (category: SuggestedQuestion["category"]) => {
    switch (category) {
      case "history":
        return <History className="w-3.5 h-3.5 text-heritage-gold" />;
      case "architecture":
        return <Landmark className="w-3.5 h-3.5 text-heritage-gold" />;
      case "sculpture":
        return <Gem className="w-3.5 h-3.5 text-heritage-gold" />;
      default:
        return <Sparkles className="w-3.5 h-3.5 text-heritage-gold" />;
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto my-6 px-4">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="w-4 h-4 text-heritage-gold" />
        <h3 className="text-xs font-bold uppercase tracking-wider text-heritage-umber dark:text-heritage-stone">
          {t.suggestedTitle}
        </h3>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {SUGGESTED_QUESTIONS.map((q) => {
          const text = language === "kn" ? q.textKn : q.textEn;
          return (
            <button
              key={q.id}
              onClick={() => onSelectQuestion(text)}
              className="text-left p-3 rounded-lg bg-heritage-ivory dark:bg-heritage-deep-stone border border-heritage-brown/10 dark:border-heritage-gold/20 hover:border-heritage-gold dark:hover:border-heritage-gold shadow-sm hover:shadow-md transition-all group focus:ring-2 focus:ring-heritage-gold"
            >
              <div className="flex items-center gap-1.5 text-[10px] font-semibold text-heritage-umber dark:text-heritage-stone uppercase mb-1">
                {getCategoryIcon(q.category)}
                <span>{q.category}</span>
              </div>
              <p className="text-xs font-medium text-heritage-brown dark:text-heritage-marble group-hover:text-heritage-gold transition-colors leading-relaxed">
                {text}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
};
