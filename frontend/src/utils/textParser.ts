export const parseBackendText = (rawText: string): string[] => {
  if (!rawText) return ["..."];

  // 1. Remove System Dividers (lines with lots of = or -)
  let cleanText = rawText.replace(/^[=\-]{3,}$/gm, '');

  // 2. Remove "Plot Deduction" or specific system prefixes
  cleanText = cleanText.replace(/💭\s*-\s*\*\*剧情推演\*\*:/g, '');
  cleanText = cleanText.replace(/【.*?】/g, ''); // Remove bracketed system notes if any

  // 3. Remove Markdown Bold/Italic artifacts (optional, but good for clean VN look)
  // cleanText = cleanText.replace(/\*\*/g, ''); 

  // 4. Split into paragraphs
  // Filter out empty lines or just whitespace
  const paragraphs = cleanText
    .split('\n')
    .map(line => line.replace(/[ \t\r]+$/g, ''))
    .filter(line => line.length > 0);

  // 5. Post-process paragraphs (optional combining of short lines?)
  // For now, return filtered paragraphs.
  if (paragraphs.length === 0) return ["..."];

  return paragraphs;
};
