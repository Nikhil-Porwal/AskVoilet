import React, { useRef, useEffect } from "react";
import { Brain, Loader2, Send, Sparkles, ChevronRight, MessageSquare } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

const MarkdownMessage = ({ content }) => (
  <div className="message-content prose prose-slate max-w-none text-[15px] leading-7">
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={{
        h1: ({ children }) => <h1 className="mb-3 mt-5 text-2xl font-bold first:mt-0">{children}</h1>,
        h2: ({ children }) => <h2 className="mb-2 mt-5 text-xl font-bold first:mt-0">{children}</h2>,
        h3: ({ children }) => <h3 className="mb-2 mt-4 text-lg font-semibold first:mt-0">{children}</h3>,
        p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="mb-3 list-disc space-y-1 pl-6">{children}</ul>,
        ol: ({ children }) => <ol className="mb-3 list-decimal space-y-1 pl-6">{children}</ol>,
        li: ({ children }) => <li className="pl-1">{children}</li>,
        blockquote: ({ children }) => (
          <blockquote className="my-3 border-l-4 border-purple-300 bg-purple-50 px-4 py-2 text-slate-700">
            {children}
          </blockquote>
        ),
        a: ({ children, href }) => (
          <a href={href} target="_blank" rel="noreferrer" className="font-medium text-purple-700 underline decoration-purple-300 underline-offset-2 hover:text-purple-900">
            {children}
          </a>
        ),
        code: ({ className, children, ...props }) => {
          const isBlock = Boolean(className);
          return isBlock ? (
            <code className={`${className} block overflow-x-auto rounded-lg bg-slate-900 p-4 text-sm leading-6 text-slate-100`} {...props}>
              {children}
            </code>
          ) : (
            <code className="rounded bg-slate-100 px-1.5 py-0.5 text-[0.9em] text-purple-700" {...props}>
              {children}
            </code>
          );
        },
        pre: ({ children }) => <pre className="mb-4 overflow-x-auto">{children}</pre>,
        table: ({ children }) => (
          <div className="mb-4 overflow-x-auto">
            <table className="min-w-full border-collapse text-sm">{children}</table>
          </div>
        ),
        th: ({ children }) => <th className="border border-slate-200 bg-slate-100 px-3 py-2 text-left font-semibold">{children}</th>,
        td: ({ children }) => <td className="border border-slate-200 px-3 py-2">{children}</td>,
      }}
    >
      {content}
    </ReactMarkdown>
  </div>
);

const ChatArea = ({
  selectedCollection,
  messages,
  insights,
  isLoading,
  currentQuestion,
  setCurrentQuestion,
  handleSendQuestion,
}) => {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (!selectedCollection) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="max-w-md text-center">
          <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-purple-100">
            <MessageSquare className="w-8 h-8 text-purple-600" />
          </div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">Choose a collection</h3>
          <p className="text-gray-500 mb-6">
            Select a collection or upload new PDFs to get started
          </p>
        </div>
      </div>
    );
  }

  return (
    <main className="app-main flex-1 flex flex-col bg-slate-50">
      {insights && messages.length === 0 && (
        <div className="bg-gradient-to-r from-purple-500 to-blue-500 text-white p-6">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="w-5 h-5" />
              <h3 className="text-lg font-semibold">AI Insights</h3>
            </div>

            <div className="bg-white/10 backdrop-blur rounded-lg p-4 mb-4">
              <h4 className="font-medium mb-2">Summary</h4>
              <p className="text-sm text-white/90">{insights.summary}</p>
            </div>

            {insights.key_concepts?.length > 0 && (
              <div className="mb-4">
                <h4 className="font-medium mb-2">Key Concepts</h4>
                <div className="flex flex-wrap gap-2">
                  {insights.key_concepts.map((concept, idx) => (
                    <span key={idx} className="px-3 py-1 bg-white/20 rounded-full text-sm">
                      {concept}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {insights.suggested_questions?.length > 0 && (
              <div>
                <h4 className="font-medium mb-2">Suggested Questions</h4>
                <div className="space-y-2">
                  {insights.suggested_questions.map((question, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendQuestion(question)}
                      className="w-full text-left px-4 py-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors text-sm flex items-center justify-between group"
                    >
                      <span>{question}</span>
                      <ChevronRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.map((message, idx) => (
            <div key={idx} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-3xl ${
                  message.role === "user"
                    ? "bg-purple-600 text-white"
                    : "bg-white border border-gray-200"
                } rounded-2xl px-6 py-4 shadow-sm`}
              >
                {message.role === "assistant" && (
                  <div className="flex items-center gap-2 mb-2">
                    <Brain className="w-4 h-4 text-purple-600" />
                    <span className="text-xs font-medium text-purple-600">AI Assistant</span>
                  </div>
                )}
                {message.role === "assistant" ? (
                  <MarkdownMessage content={message.content} />
                ) : (
                  <p className="message-content whitespace-pre-wrap">{message.content}</p>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 rounded-2xl px-6 py-4 shadow-sm">
                <div className="flex items-center gap-3">
                  <Loader2 className="w-5 h-5 text-purple-600 animate-spin" />
                  <span className="text-gray-600">Thinking...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="border-t border-gray-200 bg-white p-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-3">
            <input
              type="text"
              value={currentQuestion}
              onChange={(e) => setCurrentQuestion(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleSendQuestion()}
              placeholder="Ask a question about your documents..."
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
              disabled={isLoading}
            />
            <button
              onClick={() => handleSendQuestion()}
              disabled={isLoading || !currentQuestion.trim()}
              className="bg-purple-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
              Send
            </button>
          </div>
        </div>
      </div>
    </main>
  );
};

export default ChatArea;
