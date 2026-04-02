import sharp from 'sharp';
import fs from 'fs';
import path from 'path';

const outBase = 'C:/Users/mustwafa abubakar/fantasy bakery/showroom/public/textures';

const jobs = [
  {
    src: 'C:/Users/mustwafa abubakar/fantasy bakery/fantasy_sugar_roll.jpg',
    outDir: path.join(outBase, 'sugarRolls'),
    prefix: 'front'
  },
  {
    src: 'C:/Users/mustwafa abubakar/fantasy bakery/fantasy_buns.jpg',
    outDir: path.join(outBase, 'buns'),
    prefix: 'front'
  }
];

async function generatePBR(sourceFile, outDir, prefix) {
  if (!fs.existsSync(sourceFile)) {
    console.error(`Source not found: ${sourceFile}`);
    return;
  }

  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }

  // 1. Albedo (WebP compressed)
  await sharp(sourceFile)
    .resize(1024)
    .webp({ quality: 80 })
    .toFile(path.join(outDir, `${prefix}_albedo.webp`));

  // 2. Roughness Map 
  await sharp(sourceFile)
    .resize(1024)
    .grayscale()
    .webp({ quality: 70 })
    .toFile(path.join(outDir, `${prefix}_roughness.webp`));

  // 3. Displacement Map (Direct grayscale for depth 'bulges')
  await sharp(sourceFile)
    .resize(512) 
    .blur(1.5) 
    .grayscale()
    .webp({ quality: 70 })
    .toFile(path.join(outDir, `${prefix}_displacement.webp`));
    
  console.log(`✅ PBR maps generated for ${prefix} at ${outDir}`);
}

async function run() {
  for (const job of jobs) {
    console.log(`Processing: ${job.src}`);
    await generatePBR(job.src, job.outDir, job.prefix);
  }
  console.log('All textures generated successfully.');
}

run();
