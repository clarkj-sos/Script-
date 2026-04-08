// YouTube API response types

export interface YouTubeVideo {
  id: string;
  snippet: {
    title: string;
    description: string;
    publishedAt: string;
    channelId: string;
    channelTitle: string;
    tags?: string[];
    categoryId: string;
    thumbnails: Record<string, { url: string; width: number; height: number }>;
    defaultLanguage?: string;
    liveBroadcastContent: string;
  };
  contentDetails?: {
    duration: string;
    dimension: string;
    definition: string;
    caption: string;
    licensedContent: boolean;
  };
  statistics?: {
    viewCount: string;
    likeCount: string;
    commentCount: string;
    favoriteCount: string;
  };
  status?: {
    uploadStatus: string;
    privacyStatus: string;
    publishAt?: string;
    license: string;
    embeddable: boolean;
    madeForKids: boolean;
  };
}

export interface YouTubeChannel {
  id: string;
  snippet: {
    title: string;
    description: string;
    customUrl?: string;
    publishedAt: string;
    thumbnails: Record<string, { url: string; width: number; height: number }>;
    country?: string;
  };
  statistics?: {
    viewCount: string;
    subscriberCount: string;
    videoCount: string;
    hiddenSubscriberCount: boolean;
  };
  contentDetails?: {
    relatedPlaylists: {
      likes: string;
      uploads: string;
    };
  };
}

export interface YouTubePlaylist {
  id: string;
  snippet: {
    title: string;
    description: string;
    publishedAt: string;
    channelId: string;
    channelTitle: string;
    thumbnails: Record<string, { url: string; width: number; height: number }>;
  };
  contentDetails?: {
    itemCount: number;
  };
  status?: {
    privacyStatus: string;
  };
}

export interface YouTubePlaylistItem {
  id: string;
  snippet: {
    title: string;
    description: string;
    publishedAt: string;
    channelId: string;
    channelTitle: string;
    playlistId: string;
    position: number;
    resourceId: {
      kind: string;
      videoId: string;
    };
    thumbnails: Record<string, { url: string; width: number; height: number }>;
  };
}

export interface YouTubeSearchResult {
  id: {
    kind: string;
    videoId?: string;
    channelId?: string;
    playlistId?: string;
  };
  snippet: {
    title: string;
    description: string;
    publishedAt: string;
    channelId: string;
    channelTitle: string;
    thumbnails: Record<string, { url: string; width: number; height: number }>;
    liveBroadcastContent: string;
  };
}

export interface YouTubeComment {
  id: string;
  snippet: {
    videoId: string;
    topLevelComment?: {
      id: string;
      snippet: {
        textDisplay: string;
        authorDisplayName: string;
        authorProfileImageUrl: string;
        likeCount: number;
        publishedAt: string;
        updatedAt: string;
      };
    };
    totalReplyCount: number;
    isPublic: boolean;
  };
}

export interface PaginatedResponse<T> {
  total_results: number;
  results_per_page: number;
  items: T[];
  next_page_token?: string;
  prev_page_token?: string;
  has_more: boolean;
}
