/**
 * Material Symbols Configuration
 * This file configures and initializes Material Symbols icons for the application
 */

// Function to check if Material Symbols font is loaded
function checkMaterialSymbolsLoaded() {
  // Log for debugging
  console.log('Checking Material Symbols font loading...');
  
  // Create a span with a material symbol to test
  const testEl = document.createElement('span');
  testEl.className = 'material-symbols-outlined';
  testEl.textContent = 'check';
  testEl.style.position = 'absolute';
  testEl.style.opacity = '0';
  
  // Add to DOM temporarily to check rendering
  document.body.appendChild(testEl);
  
  // Get computed style and check if font is loaded
  const computedStyle = window.getComputedStyle(testEl);
  const fontFamily = computedStyle.getPropertyValue('font-family');
  
  // Clean up
  document.body.removeChild(testEl);
  
  // Log font status
  const isFontLoaded = fontFamily.includes('Material Symbols Outlined');
  console.log(`Material Symbols font loaded: ${isFontLoaded}`);
  
  // If not loaded, try to reload or notify
  if (!isFontLoaded) {
    console.warn('Material Symbols font not loaded correctly. Attempting to reload...');
    // Attempt to reload the font by adding the link dynamically
    ensureFontIsLoaded();
  }
}

// Function to ensure the font is loaded
function ensureFontIsLoaded() {
  // Check if we already have the Material Symbols font links
  const existingOutlinedLink = document.querySelector('link[href*="Material+Symbols+Outlined"]');
  const existingRoundedLink = document.querySelector('link[href*="Material+Symbols+Rounded"]');
  const existingFilledLink = document.querySelector('link[href*="Material+Symbols+Sharp"]');
  
  // Add Outlined variant if needed
  if (!existingOutlinedLink) {
    console.log('Adding Material Symbols Outlined font link dynamically');
    const fontLink = document.createElement('link');
    fontLink.rel = 'stylesheet';
    fontLink.href = 'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,0..200';
    document.head.appendChild(fontLink);
  }
  
  // Add Rounded variant if needed
  if (!existingRoundedLink) {
    console.log('Adding Material Symbols Rounded font link dynamically');
    const fontLink = document.createElement('link');
    fontLink.rel = 'stylesheet';
    fontLink.href = 'https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,0..200';
    document.head.appendChild(fontLink);
  }
  
  // Add Filled variant if needed
  if (!existingFilledLink) {
    console.log('Adding Material Symbols Sharp font link dynamically');
    const fontLink = document.createElement('link');
    fontLink.rel = 'stylesheet';
    fontLink.href = 'https://fonts.googleapis.com/css2?family=Material+Symbols+Sharp:opsz,wght,FILL,GRAD@20..48,100..700,0..1,0..200';
    document.head.appendChild(fontLink);
  }
  
  // Add a specific set of icons with FILL=1 for filled variants
  const filledIconsLink = document.createElement('link');
  filledIconsLink.rel = 'stylesheet';
  filledIconsLink.href = 'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,1,0&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,1,0';
  document.head.appendChild(filledIconsLink);
}

// Initialize when DOM is loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
      ensureFontIsLoaded(); // Always load fonts
      setTimeout(checkMaterialSymbolsLoaded, 1000); // Then check if loaded correctly
    }, 500);
  });
} else {
  // DOM already loaded, load fonts immediately
  ensureFontIsLoaded();
  setTimeout(checkMaterialSymbolsLoaded, 1000);
}

// Add CSS rules for filled icons
const addFilledIconStyles = () => {
  const styleEl = document.createElement('style');
  styleEl.textContent = `
    .material-icons-filled, 
    .material-symbols-filled {
      font-variation-settings: 'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24;
    }
    .material-icons-outlined,
    .material-symbols-outlined {
      font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
    }
    .icon-maroon {
      color: #722b2b !important;
    }
  `;
  document.head.appendChild(styleEl);
};

// Add the styles when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', addFilledIconStyles);
} else {
  addFilledIconStyles();
}

// Export for explicit import if needed
export default {
  checkMaterialSymbolsLoaded,
  ensureFontIsLoaded
}; 