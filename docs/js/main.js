/**
 * Talons for Grabbit - Main Client Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  initThemeToggle();
  initMobileNav();
  initReviews();
  initLatestRelease();
  initSmoothScroll();
});

// Dark & Light Mode Switcher
function initThemeToggle() {
  const toggleBtn = document.getElementById('themeToggleBtn');
  if (!toggleBtn) return;

  function getActiveTheme() {
    const saved = localStorage.getItem('talons-theme');
    if (saved) return saved;
    return (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) ? 'light' : 'dark';
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('talons-theme', theme);
  }

  // Set initial
  applyTheme(getActiveTheme());

  toggleBtn.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
    applyTheme(nextTheme);
  });

  // Listen to OS theme changes if user hasn't explicitly set one
  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', e => {
      if (!localStorage.getItem('talons-theme')) {
        applyTheme(e.matches ? 'light' : 'dark');
      }
    });
  }
}

// Mobile Navigation Toggle
function initMobileNav() {
  const burger = document.querySelector('.header__burger');
  const nav = document.querySelector('.header__nav');

  if (burger && nav) {
    burger.addEventListener('click', () => {
      nav.classList.toggle('active');
    });

    // Close when clicking a link
    nav.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        nav.classList.remove('active');
      });
    });
  }
}


// Toast Alert
function showToast(message) {
  let toast = document.getElementById('liveToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'liveToast';
    toast.className = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add('show');
  setTimeout(() => {
    toast.classList.remove('show');
  }, 3000);
}

// Dynamic GitHub Release asset linker
function initLatestRelease() {
  const downloadBtn = document.getElementById('downloadBtn');
  const repoOwner = 'grabbit';
  const repoName = 'grabbit-ytdlp-plugin';

  if (downloadBtn) {
    // Fallback release URL
    const defaultUrl = `https://github.com/${repoOwner}/${repoName}/releases/latest/download/talons.gda`;
    downloadBtn.setAttribute('href', defaultUrl);

    // Attempt to fetch latest tag via GitHub API
    fetch(`https://api.github.com/repos/${repoOwner}/${repoName}/releases/latest`)
      .then(res => res.json())
      .then(data => {
        if (data && data.assets) {
          const asset = data.assets.find(a => a.name.endsWith('.gda'));
          if (asset && asset.browser_download_url) {
            downloadBtn.setAttribute('href', asset.browser_download_url);
            const verTag = document.getElementById('releaseVersionTag');
            if (verTag && data.tag_name) {
              verTag.textContent = data.tag_name;
            }
          }
        }
      })
      .catch(() => {
        // Safe fallback already applied
      });
  }
}

// Star Rating and Reviews
function initReviews() {
  const starsContainer = document.getElementById('starRatingPicker');
  const ratingInput = document.getElementById('ratingValue');
  const form = document.getElementById('reviewForm');
  const reviewsContainer = document.getElementById('reviewsContainer');

  let selectedRating = 5;

  if (starsContainer) {
    const stars = starsContainer.querySelectorAll('.star-choice');
    
    function highlightStars(count) {
      stars.forEach((star, index) => {
        if (index < count) {
          star.classList.add('active');
          star.textContent = '★';
        } else {
          star.classList.remove('active');
          star.textContent = '☆';
        }
      });
    }

    stars.forEach(star => {
      star.addEventListener('mouseenter', () => {
        const rating = parseInt(star.getAttribute('data-rating'), 10);
        highlightStars(rating);
      });

      star.addEventListener('click', () => {
        selectedRating = parseInt(star.getAttribute('data-rating'), 10);
        if (ratingInput) ratingInput.value = selectedRating;
        highlightStars(selectedRating);
      });
    });

    starsContainer.addEventListener('mouseleave', () => {
      highlightStars(selectedRating);
    });

    // Default 5 stars
    highlightStars(selectedRating);
  }

  // Load existing reviews from localStorage
  const savedReviews = JSON.parse(localStorage.getItem('talons_user_reviews') || '[]');
  savedReviews.forEach(r => renderReview(r, false));

  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const name = document.getElementById('reviewerName').value.trim() || 'Anonymous';
      const comment = document.getElementById('reviewerComment').value.trim();

      if (!comment) {
        showToast('Please enter a comment before submitting.');
        return;
      }

      const newReview = {
        name,
        comment,
        rating: selectedRating,
        date: new Date().toLocaleDateString()
      };

      savedReviews.unshift(newReview);
      localStorage.setItem('talons_user_reviews', JSON.stringify(savedReviews));
      renderReview(newReview, true);

      // Reset form
      form.reset();
      selectedRating = 5;
      if (starsContainer) {
        const stars = starsContainer.querySelectorAll('.star-choice');
        stars.forEach(star => {
          star.classList.add('active');
          star.textContent = '★';
        });
      }

      showToast('Thank you! Your review has been posted.');
    });
  }

  function renderReview(review, prepend = false) {
    if (!reviewsContainer) return;
    const item = document.createElement('div');
    item.className = 'review_entry';
    
    const starsHtml = '★'.repeat(review.rating) + '☆'.repeat(5 - review.rating);

    item.innerHTML = `
      <div class="review_entry_top">
        <span class="review_entry_name">${escapeHTML(review.name)}</span>
        <span class="review_entry_stars">${starsHtml}</span>
      </div>
      <p class="review_entry_comment">${escapeHTML(review.comment)}</p>
    `;

    if (prepend && reviewsContainer.firstChild) {
      reviewsContainer.insertBefore(item, reviewsContainer.firstChild);
    } else {
      reviewsContainer.appendChild(item);
    }
  }

  function escapeHTML(str) {
    return str.replace(/[&<>'"]/g, 
      tag => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        "'": '&#39;',
        '"': '&quot;'
      }[tag] || tag)
    );
  }
}

// Smooth scrolling for navigation links
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const targetId = this.getAttribute('href');
      if (targetId && targetId !== '#') {
        const targetElement = document.querySelector(targetId);
        if (targetElement) {
          e.preventDefault();
          targetElement.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
          });
        }
      }
    });
  });
}
