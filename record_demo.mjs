import puppeteer from 'puppeteer';
import fs from 'fs';
import path from 'path';

const framesDir = path.join(process.cwd(), 'frames');
if (fs.existsSync(framesDir)) {
  fs.rmSync(framesDir, { recursive: true, force: true });
}
fs.mkdirSync(framesDir, { recursive: true });

let frameIndex = 0;

async function captureFrames(page, durationMs, fps = 8) {
  const interval = 1000 / fps;
  const count = Math.ceil(durationMs / interval);
  for (let i = 0; i < count; i++) {
    const filename = path.join(framesDir, `frame_${String(frameIndex++).padStart(5, '0')}.png`);
    await page.screenshot({ path: filename, type: 'png' });
    await new Promise(r => setTimeout(r, interval));
  }
}

async function typeText(page, selector, text) {
  for (const char of text) {
    await page.type(selector, char, { delay: 35 });
    const filename = path.join(framesDir, `frame_${String(frameIndex++).padStart(5, '0')}.png`);
    await page.screenshot({ path: filename, type: 'png' });
  }
}

async function waitForNewAgentResponse(page, previousCount, maxWaitSeconds = 30) {
  console.log(`Waiting for agent response #${previousCount + 1}...`);
  for (let s = 0; s < maxWaitSeconds; s++) {
    await captureFrames(page, 1000, 6);
    const ready = await page.evaluate((prev) => {
      const bubbles = Array.from(document.querySelectorAll('.msg.agent .bubble'));
      if (bubbles.length > prev) {
        const last = bubbles[bubbles.length - 1];
        const txt = (last.textContent || "").trim();
        if (txt !== "…" && txt.length > 20) {
          return true;
        }
      }
      return false;
    }, previousCount);

    if (ready) {
      console.log(`Agent response #${previousCount + 1} fully rendered!`);
      return true;
    }
  }
  console.log(`Warning: Timeout waiting for agent response #${previousCount + 1}`);
  return false;
}

(async () => {
  console.log('Launching browser for updated prompt demo recording...');
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/google-chrome',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--window-size=1280,800'],
    headless: true
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });

  console.log('Navigating to ER Triage Coordinator...');
  await page.goto('https://er-triage-frontend-4722205683.us-east1.run.app', { waitUntil: 'networkidle2' });
  
  // Hold intro view
  console.log('Capturing intro page...');
  await captureFrames(page, 2000, 8);

  let initialAgentCount = await page.evaluate(() => document.querySelectorAll('.msg.agent .bubble').length);
  console.log(`Initial agent bubbles on page: ${initialAgentCount}`);

  // 1. First Prompt: Core App Capability (New Clinical Scenario: Severe Respiratory Distress Intake)
  console.log('Typing new prompt 1: Clinical ESI Triage Intake for acute respiratory distress...');
  const prompt1 = 'Triage 68yo female with acute shortness of breath, wheezing, SpO2 86%, and history of asthma';
  await typeText(page, '#input', prompt1);
  await captureFrames(page, 500, 8);

  console.log('Sending prompt 1...');
  await page.keyboard.press('Enter');

  // Wait specifically for prompt 1 response to finish rendering
  await waitForNewAgentResponse(page, initialAgentCount, 25);
  await captureFrames(page, 4000, 8);

  let secondAgentCount = await page.evaluate(() => document.querySelectorAll('.msg.agent .bubble').length);

  // 2. Second Richer Prompt: Tool Call + Database Lookup + Real Time Dashboard Image of Departmental Wait Times
  console.log('Typing new rich prompt 2: Tool call, DB lookup & generated dashboard image of departmental wait times...');
  const prompt2 = 'Check active patient queue in Firestore DB, execute bed status lookup tool, and call generate_departmental_wait_times_dashboard_image to create a real time dashboard image of departmental wait times';
  await typeText(page, '#input', prompt2);
  await captureFrames(page, 500, 8);

  console.log('Sending rich prompt 2...');
  await page.keyboard.press('Enter');

  // Wait specifically for prompt 2 response (with generated image and dashboard) to finish rendering
  await waitForNewAgentResponse(page, secondAgentCount, 35);
  await captureFrames(page, 5000, 8);

  // 3. Interactive Bed Map & Patient Queue Drawer Demonstration
  console.log('Opening Map & Queue drawer...');
  await page.evaluate(() => {
    if (typeof toggleDrawer === 'function') toggleDrawer();
  });
  await captureFrames(page, 2000, 8);

  console.log('Clicking Trauma filter pill...');
  await page.evaluate(() => {
    const pills = Array.from(document.querySelectorAll('.unit-pill'));
    const trauma = pills.find(p => p.textContent.includes('Trauma'));
    if (trauma) trauma.click();
  });
  await captureFrames(page, 1800, 8);

  console.log('Clicking Cardiac Care filter pill...');
  await page.evaluate(() => {
    const pills = Array.from(document.querySelectorAll('.unit-pill'));
    const cardiac = pills.find(p => p.textContent.includes('Cardiac'));
    if (cardiac) cardiac.click();
  });
  await captureFrames(page, 1800, 8);

  console.log('Clicking All Beds filter pill...');
  await page.evaluate(() => {
    const pills = Array.from(document.querySelectorAll('.unit-pill'));
    const all = pills.find(p => p.textContent.includes('All Beds'));
    if (all) all.click();
  });
  await captureFrames(page, 2500, 8);

  console.log('Finished capturing new demo screenshots! Total frames:', frameIndex);
  await browser.close();
})();
