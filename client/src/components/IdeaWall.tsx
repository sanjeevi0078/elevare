"use client";

import { useState, useEffect, useCallback } from "react";

// =============================================================================
// TYPE DEFINITIONS
// =============================================================================

interface Idea {
  id: number;
  title: string;
  description: string;
  category: string;
  user_id: number;
  user_name?: string;
  likes: number;
  created_at: string;
  tags?: string[];
  status?: string;
}

interface ApiResponse {
  ideas: Idea[];
  total: number;
  page: number;
  per_page: number;
}

// =============================================================================
// CONFIGURATION
// =============================================================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// =============================================================================
// IDEA CARD COMPONENT
// =============================================================================

function IdeaCard({
  idea,
  onLike,
  isLiking,
}: {
  idea: Idea;
  onLike: (id: number) => void;
  isLiking: boolean;
}) {
  const formattedDate = new Date(idea.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  const categoryColors: Record<string, string> = {
    technology: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    health: "bg-green-500/20 text-green-400 border-green-500/30",
    finance: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    education: "bg-purple-500/20 text-purple-400 border-purple-500/30",
    sustainability: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    default: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  };

  const categoryColor =
    categoryColors[idea.category?.toLowerCase()] || categoryColors.default;

  return (
    <div className="group relative bg-gradient-to-br from-gray-900 to-gray-800 rounded-2xl p-6 border border-gray-700/50 hover:border-purple-500/50 transition-all duration-300 hover:shadow-xl hover:shadow-purple-500/10">
      {/* Category Badge */}
      <div className="flex items-center justify-between mb-4">
        <span
          className={`px-3 py-1 rounded-full text-xs font-medium border ${categoryColor}`}
        >
          {idea.category || "General"}
        </span>
        <span className="text-gray-500 text-sm">{formattedDate}</span>
      </div>

      {/* Title */}
      <h3 className="text-xl font-bold text-white mb-3 group-hover:text-purple-400 transition-colors">
        {idea.title}
      </h3>

      {/* Description */}
      <p className="text-gray-400 text-sm leading-relaxed mb-4 line-clamp-3">
        {idea.description}
      </p>

      {/* Tags */}
      {idea.tags && idea.tags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {idea.tags.slice(0, 3).map((tag, index) => (
            <span
              key={index}
              className="px-2 py-1 bg-gray-700/50 text-gray-300 rounded-md text-xs"
            >
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-700/50">
        {/* Author */}
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white text-sm font-bold">
            {idea.user_name?.charAt(0) || "U"}
          </div>
          <span className="text-gray-400 text-sm">
            {idea.user_name || `User ${idea.user_id}`}
          </span>
        </div>

        {/* Like Button */}
        <button
          onClick={() => onLike(idea.id)}
          disabled={isLiking}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-200 ${
            isLiking
              ? "bg-gray-700 cursor-not-allowed"
              : "bg-gray-700/50 hover:bg-purple-500/20 hover:text-purple-400"
          }`}
        >
          <svg
            className={`w-5 h-5 ${isLiking ? "animate-pulse" : ""}`}
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z"
              clipRule="evenodd"
            />
          </svg>
          <span className="font-medium">{idea.likes}</span>
        </button>
      </div>
    </div>
  );
}

// =============================================================================
// LOADING SKELETON
// =============================================================================

function IdeaCardSkeleton() {
  return (
    <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-2xl p-6 border border-gray-700/50 animate-pulse">
      <div className="flex items-center justify-between mb-4">
        <div className="h-6 w-24 bg-gray-700 rounded-full"></div>
        <div className="h-4 w-20 bg-gray-700 rounded"></div>
      </div>
      <div className="h-6 w-3/4 bg-gray-700 rounded mb-3"></div>
      <div className="space-y-2 mb-4">
        <div className="h-4 w-full bg-gray-700 rounded"></div>
        <div className="h-4 w-5/6 bg-gray-700 rounded"></div>
      </div>
      <div className="flex items-center justify-between pt-4 border-t border-gray-700/50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-gray-700"></div>
          <div className="h-4 w-20 bg-gray-700 rounded"></div>
        </div>
        <div className="h-8 w-16 bg-gray-700 rounded-lg"></div>
      </div>
    </div>
  );
}

// =============================================================================
// MAIN IDEA WALL COMPONENT
// =============================================================================

export default function IdeaWall() {
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [likingIds, setLikingIds] = useState<Set<number>>(new Set());
  const [filter, setFilter] = useState<string>("all");

  // Fetch ideas from API
  const fetchIdeas = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/ideas/public`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch ideas: ${response.status}`);
      }

      const data: ApiResponse = await response.json();
      setIdeas(data.ideas || []);
    } catch (err) {
      console.error("Error fetching ideas:", err);
      setError(err instanceof Error ? err.message : "Failed to load ideas");
      
      // Fallback: Try alternative endpoint
      try {
        const fallbackResponse = await fetch(`${API_BASE_URL}/api/ideas`, {
          method: "GET",
          headers: { "Content-Type": "application/json" },
        });
        
        if (fallbackResponse.ok) {
          const fallbackData = await fallbackResponse.json();
          setIdeas(fallbackData.ideas || fallbackData || []);
          setError(null);
        }
      } catch {
        // Keep original error
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // Handle like (Optimistic UI Update)
  const handleLike = async (ideaId: number) => {
    // Prevent double-clicking
    if (likingIds.has(ideaId)) return;

    // Optimistic update - immediately update UI
    setIdeas((prevIdeas) =>
      prevIdeas.map((idea) =>
        idea.id === ideaId ? { ...idea, likes: idea.likes + 1 } : idea
      )
    );

    // Track that we're liking this idea
    setLikingIds((prev) => new Set(prev).add(ideaId));

    try {
      const response = await fetch(`${API_BASE_URL}/ideas/${ideaId}/like`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        // Rollback on error
        setIdeas((prevIdeas) =>
          prevIdeas.map((idea) =>
            idea.id === ideaId ? { ...idea, likes: idea.likes - 1 } : idea
          )
        );
        throw new Error("Failed to like idea");
      }
    } catch (err) {
      console.error("Error liking idea:", err);
    } finally {
      // Remove from liking set
      setLikingIds((prev) => {
        const next = new Set(prev);
        next.delete(ideaId);
        return next;
      });
    }
  };

  // Fetch on mount
  useEffect(() => {
    fetchIdeas();
  }, [fetchIdeas]);

  // Get unique categories for filter
  const categories = ["all", ...new Set(ideas.map((i) => i.category?.toLowerCase() || "general"))];

  // Filter ideas
  const filteredIdeas =
    filter === "all"
      ? ideas
      : ideas.filter((i) => i.category?.toLowerCase() === filter);

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-950 via-gray-900 to-gray-950">
      {/* Header */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-purple-400 via-pink-500 to-red-500 bg-clip-text text-transparent mb-4">
            Global Idea Wall
          </h1>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Discover innovative startup ideas from founders around the world.
            Like and support the ones that inspire you.
          </p>
        </div>

        {/* Filter Bar */}
        <div className="flex flex-wrap justify-center gap-3 mb-8">
          {categories.map((category) => (
            <button
              key={category}
              onClick={() => setFilter(category)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
                filter === category
                  ? "bg-purple-500 text-white shadow-lg shadow-purple-500/25"
                  : "bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white"
              }`}
            >
              {category.charAt(0).toUpperCase() + category.slice(1)}
            </button>
          ))}
        </div>

        {/* Error State */}
        {error && (
          <div className="max-w-md mx-auto mb-8 p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-center">
            <p>{error}</p>
            <button
              onClick={fetchIdeas}
              className="mt-3 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 rounded-lg transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        {/* Ideas Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {loading ? (
            // Loading skeletons
            Array.from({ length: 6 }).map((_, i) => <IdeaCardSkeleton key={i} />)
          ) : filteredIdeas.length === 0 ? (
            // Empty state
            <div className="col-span-full text-center py-16">
              <div className="text-6xl mb-4">💡</div>
              <h3 className="text-xl font-semibold text-white mb-2">
                No ideas yet
              </h3>
              <p className="text-gray-400">
                Be the first to share your startup idea!
              </p>
            </div>
          ) : (
            // Ideas list
            filteredIdeas.map((idea) => (
              <IdeaCard
                key={idea.id}
                idea={idea}
                onLike={handleLike}
                isLiking={likingIds.has(idea.id)}
              />
            ))
          )}
        </div>

        {/* Stats Footer */}
        {!loading && ideas.length > 0 && (
          <div className="mt-12 text-center text-gray-500">
            <p>
              Showing {filteredIdeas.length} of {ideas.length} ideas
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
