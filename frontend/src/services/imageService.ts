/**
 * 生图服务 - 接入 Gemini Image Generation API
 */

export interface ImageGenerationResult {
  imageUrl: string;
  cached: boolean;
}

// 简单的内存缓存
const imageCache = new Map<string, string>();

// API 配置
const API_URL = 'https://kkkopenai.3kxyz.com/v1/chat/completions';
const API_KEY = 'sk-qNo8npkRdiC91y1zbKSbcSX87vxmY3dCtGYW0VbcjL9eJnzC';
const MODEL = 'gemini-3-pro-image-preview';

/**
 * 生成图片
 */
export async function generateImage(
  prompt: string,
  _negativePrompt?: string
): Promise<ImageGenerationResult> {
  // 检查缓存
  const cacheKey = hashCode(prompt).toString();
  if (imageCache.has(cacheKey)) {
    console.log('🎨 使用缓存图片');
    return { imageUrl: imageCache.get(cacheKey)!, cached: true };
  }

  try {
    console.log('🎨 开始生成图片...');
    const imageUrl = await callGeminiImageAPI(prompt);

    // 缓存结果
    imageCache.set(cacheKey, imageUrl);
    console.log('🎨 图片生成完成');

    return { imageUrl, cached: false };
  } catch (error) {
    console.error('生图失败，使用 placeholder:', error);
    // 降级到 placeholder
    const fallbackUrl = `https://picsum.photos/seed/${hashCode(prompt)}/1920/1080`;
    return { imageUrl: fallbackUrl, cached: false };
  }
}

/**
 * 调用 Gemini Image API（流式）
 */
async function callGeminiImageAPI(prompt: string): Promise<string> {
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${API_KEY}`,
    },
    body: JSON.stringify({
      model: MODEL,
      messages: [
        {
          role: 'user',
          content: `Generate a high quality cinematic image: ${prompt}`
        }
      ],
      stream: true,
    }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  // 读取流式响应
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let fullContent = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ') && line !== 'data: [DONE]') {
        try {
          const data = JSON.parse(line.slice(6));
          const content = data.choices?.[0]?.delta?.content || '';
          fullContent += content;
        } catch {
          // 忽略解析错误
        }
      }
    }
  }

  // 提取 data URL
  const match = fullContent.match(/data:image\/(jpeg|png);base64,[A-Za-z0-9+/=]+/);
  if (match) {
    return match[0];
  }

  throw new Error('No image data in response');
}

/**
 * 字符串哈希
 */
function hashCode(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash);
}

/**
 * 清除缓存
 */
export function clearImageCache(): void {
  imageCache.clear();
}
