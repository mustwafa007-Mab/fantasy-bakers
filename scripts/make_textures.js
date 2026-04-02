import sharp from 'sharp';
import fs from 'fs';
import path from 'path';

// Define the source artifacts (media__ from Antigravity)
const srcFront = 'C:/Users/mustwafa abubakar/.gemini/antigravity/brain/864d0df2-1ba2-4904-9277-8f488f12926a/media__1775013995656.png';
const srcBottom = 'C:/Users/mustwafa abubakar/.gemini/antigravity/brain/864d0df2-1ba2-4904-9277-8f488f12926a/media__1775013995709.png';
const outDir = 'C:/Users/mustwafa abubakar/fantasy bakery/showroom/public/textures/bread';

async function generatePBR(sourceFile, prefix) {
  if (!fs.existsSync(sourceFile)) {
    console.error(`Source not found: ${sourceFile}`);
    return;
  }
  
  // 1. Albedo (WebP compressed)
  await sharp(sourceFile)
    .resize(1024)
    .webp({ quality: 80 })
    .toFile(path.join(outDir, `${prefix}_albedo.webp`));

  // 2. Roughness Map (Inverted/tweaked grayscale for shiny plastic vs matte bread)
  // Plastic has highlights (bright reflection) and shadows. We want shiny plastic = low roughness (dark).
  await sharp(sourceFile)
    .resize(1024)
    .grayscale()
    .linear(0.8, -30) // Darken slightly to make it shinier
    .webp({ quality: 70 })
    .toFile(path.join(outDir, `${prefix}_roughness.webp`));

  // 3. Displacement Map (Direct grayscale for depth 'bulges')
  // We want the bread shape to bulge outwards (lighter = higher).
  await sharp(sourceFile)
    .resize(512) // Displacement doesn't usually need to be 1024
    .blur(1.5) // Soften normals
    .grayscale()
    .webp({ quality: 70 })
    .toFile(path.join(outDir, `${prefix}_displacement.webp`));
    
  console.log(`✅ PBR maps generated for ${prefix}`);
}

async function run() {
  await generatePBR(srcFront, 'front');
  await generatePBR(srcBottom, 'bottom');
}

run();
