// Mobile question card expand/collapse
function toggleMobileExpand(card) {
    const expandedContent = card.querySelector('.mobile-expanded-content');
    const expandBtn = card.querySelector('.mobile-expand-btn');
    const icon = expandBtn.querySelector('i');
    const stemPreview = card.querySelector('.mobile-stem-preview');
    const stemFull = card.querySelector('.mobile-stem-full');
    
    if (expandedContent.style.display === 'none' || !expandedContent.style.display) {
        // Expand
        expandedContent.style.display = 'block';
        if (stemFull) {
            stemPreview.style.display = 'none';
            stemFull.style.display = 'block';
        }
        icon.className = 'fas fa-chevron-up';
        expandBtn.classList.add('expanded');
    } else {
        // Collapse
        expandedContent.style.display = 'none';
        if (stemFull) {
            stemPreview.style.display = 'block';
            stemFull.style.display = 'none';
        }
        icon.className = 'fas fa-chevron-down';
        expandBtn.classList.remove('expanded');
    }
}

// Helper functions for template rendering (these would be Python functions)
function get_type_icon(type) {
    if (!type) return 'fas fa-question-circle';
    switch(type.toLowerCase()) {
        case '单选题': return 'fas fa-check-circle';
        case '多选题': return 'fas fa-check-square';
        case '判断题': return 'fas fa-toggle-on';
        case '填空题': return 'fas fa-edit';
        default: return 'fas fa-question-circle';
    }
}

function get_difficulty_icon(difficulty) {
    if (!difficulty) return 'fas fa-minus';
    switch(difficulty.toLowerCase()) {
        case '简单': return 'fas fa-chevron-down';
        case '中等': return 'fas fa-minus';
        case '困难': return 'fas fa-chevron-up';
        default: return 'fas fa-minus';
    }
}

function get_difficulty_color(difficulty) {
    if (!difficulty) return '#6c757d';
    switch(difficulty.toLowerCase()) {
        case '简单': return '#28a745';
        case '中等': return '#ffc107';
        case '困难': return '#dc3545';
        default: return '#6c757d';
    }
}

// Desktop filter and search functions
function clearSearchFilter() {
    const currentUrl = new URL(window.location);
    currentUrl.searchParams.delete('search');
    currentUrl.searchParams.delete('page');
    window.location.href = currentUrl.toString();
}

function clearTypeFilter() {
    const currentUrl = new URL(window.location);
    currentUrl.searchParams.delete('type');
    currentUrl.searchParams.delete('page');
    window.location.href = currentUrl.toString();
}

function clearAllFilters() {
    const currentUrl = new URL(window.location);
    currentUrl.searchParams.delete('search');
    currentUrl.searchParams.delete('type');
    currentUrl.searchParams.delete('page');
    window.location.href = currentUrl.toString();
}

function resetAdvancedFilter() {
    // Reset all form inputs in the modal
    const form = document.getElementById('advancedFilterForm');
    if (form) {
        form.reset();
        // Set default values
        document.getElementById('advancedTypeAll').checked = true;
        document.getElementById('categoryAll').checked = true;
        document.getElementById('advancedSearchInput').value = '';
    }
}

function clearAllAdvancedFilters() {
    resetAdvancedFilter();
    clearAllFilters();
}

function applyAdvancedFilter() {
    const currentUrl = new URL(window.location);
    currentUrl.searchParams.delete('page'); // Reset to first page
    
    // Get selected type
    const selectedType = document.querySelector('input[name="advancedType"]:checked');
    if (selectedType && selectedType.value !== 'all') {
        currentUrl.searchParams.set('type', selectedType.value);
    } else {
        currentUrl.searchParams.delete('type');
    }
    
    // Get search term
    const searchTerm = document.getElementById('advancedSearchInput').value.trim();
    if (searchTerm) {
        currentUrl.searchParams.set('search', searchTerm);
    } else {
        currentUrl.searchParams.delete('search');
    }
    
    // Close modal and navigate
    const modal = bootstrap.Modal.getInstance(document.getElementById('advancedFilterModal'));
    if (modal) modal.hide();
    
    window.location.href = currentUrl.toString();
}

document.addEventListener('DOMContentLoaded', function() {
    // Desktop search functionality
    const desktopSearchInput = document.getElementById('desktopSearchInput');
    const desktopSearchClear = document.getElementById('desktopSearchClear');
    const desktopTypeFilter = document.getElementById('desktopTypeFilter');
    
    if (desktopSearchInput) {
        desktopSearchInput.addEventListener('input', function() {
            const hasValue = this.value.trim().length > 0;
            desktopSearchClear.style.display = hasValue ? 'block' : 'none';
            
            // Debounce search
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                const searchTerm = this.value.trim();
                const currentUrl = new URL(window.location);
                if (searchTerm) {
                    currentUrl.searchParams.set('search', searchTerm);
                } else {
                    currentUrl.searchParams.delete('search');
                }
                currentUrl.searchParams.delete('page'); // Reset to first page
                window.location.href = currentUrl.toString();
            }, 800);
        });
    }
    
    if (desktopSearchClear) {
        desktopSearchClear.addEventListener('click', function() {
            desktopSearchInput.value = '';
            this.style.display = 'none';
            clearSearchFilter();
        });
    }
    
    if (desktopTypeFilter) {
        desktopTypeFilter.addEventListener('change', function() {
            const currentUrl = new URL(window.location);
            if (this.value === 'all') {
                currentUrl.searchParams.delete('type');
            } else {
                currentUrl.searchParams.set('type', this.value);
            }
            currentUrl.searchParams.delete('page'); // Reset to first page
            window.location.href = currentUrl.toString();
        });
    }
    
    // Initialize advanced filter modal with current values
    const advancedModal = document.getElementById('advancedFilterModal');
    if (advancedModal) {
        advancedModal.addEventListener('show.bs.modal', function() {
            // Set current type selection
            const currentType = new URLSearchParams(window.location.search).get('type') || 'all';
            const typeRadio = document.querySelector(`input[name="advancedType"][value="${currentType}"]`);
            if (typeRadio) typeRadio.checked = true;
            
            // Set current search term
            const currentSearch = new URLSearchParams(window.location.search).get('search') || '';
            const searchInput = document.getElementById('advancedSearchInput');
            if (searchInput) searchInput.value = currentSearch;
        });
    }

    // Desktop page jump validation
    const desktopPageJumpForm = document.getElementById('desktopPageJumpForm');
    if (desktopPageJumpForm) {
        desktopPageJumpForm.addEventListener('submit', function(e) {
            const pageInput = this.querySelector('input[name="page"]');
            const pageValue = parseInt(pageInput.value);
            const maxPages = parseInt(pageInput.getAttribute('max'));
            const minPages = parseInt(pageInput.getAttribute('min'));
            
            if (!pageValue || pageValue < minPages || pageValue > maxPages) {
                e.preventDefault();
                pageInput.focus();
                pageInput.style.borderColor = '#dc3545';
                pageInput.style.boxShadow = '0 0 0 0.2rem rgba(220, 53, 69, 0.25)';
                
                // Show error message
                let errorMsg = pageInput.parentNode.querySelector('.error-message');
                if (!errorMsg) {
                    errorMsg = document.createElement('div');
                    errorMsg.className = 'error-message small text-danger mt-1';
                    pageInput.parentNode.appendChild(errorMsg);
                }
                errorMsg.textContent = `请输入 ${minPages} 到 ${maxPages} 之间的页码`;
                
                // Clear error after 3 seconds
                setTimeout(() => {
                    if (errorMsg) errorMsg.remove();
                    pageInput.style.borderColor = '';
                    pageInput.style.boxShadow = '';
                }, 3000);
                
                return false;
            }
        });
        
        // Clear error on input
        const pageInput = desktopPageJumpForm.querySelector('input[name="page"]');
        if (pageInput) {
            pageInput.addEventListener('input', function() {
                this.style.borderColor = '';
                this.style.boxShadow = '';
                const errorMsg = this.parentNode.querySelector('.error-message');
                if (errorMsg) errorMsg.remove();
            });
        }
    }

    // Desktop toggle expand/collapse functionality
    document.querySelectorAll('.toggle-expand').forEach(button => {
        button.addEventListener('click', function() {
            const questionItem = this.closest('.question-item');
            const expandedContent = questionItem.querySelector('.question-expanded-content');
            const icon = this.querySelector('i');
            
            if (expandedContent.style.display === 'none' || !expandedContent.style.display) {
                expandedContent.style.display = 'block';
                icon.className = 'fas fa-chevron-up';
                this.classList.add('expanded');
                this.title = '收起';
            } else {
                expandedContent.style.display = 'none';
                icon.className = 'fas fa-chevron-down';
                this.classList.remove('expanded');
                this.title = '展开';
            }
        });
    });
    
    // Mobile search functionality
    const searchInput = document.getElementById('mobileSearchInput');
    const searchClear = document.getElementById('mobileSearchClear');
    const questionsList = document.getElementById('mobileQuestionsList');
    const emptySearch = document.getElementById('mobileEmptySearch');
    const filteredCount = document.getElementById('filtered-count');
    
    if (searchInput && questionsList) {
        let allQuestions = Array.from(questionsList.querySelectorAll('.mobile-question-card'));
        let currentFilter = 'all';
        
        // Initialize filter chips
        initializeFilterChips();
        
        function initializeFilterChips() {
            const filterChips = document.getElementById('mobileFilterChips');
            if (!filterChips) return;
            
            // Get unique question types
            const types = new Set();
            allQuestions.forEach(card => {
                const type = card.getAttribute('data-question-type');
                if (type && type.trim()) {
                    types.add(type);
                }
            });
            
            // Create filter chips
            types.forEach(type => {
                const chip = document.createElement('div');
                chip.className = 'filter-chip';
                chip.dataset.filter = type;
                chip.innerHTML = `<span>${type}</span>`;
                chip.addEventListener('click', () => setFilter(type));
                filterChips.appendChild(chip);
            });
        }
        
        function setFilter(filter) {
            // Redirect with filter parameter
            const currentUrl = new URL(window.location);
            if (filter === 'all') {
                currentUrl.searchParams.delete('type');
            } else {
                currentUrl.searchParams.set('type', filter);
            }
            currentUrl.searchParams.delete('page'); // Reset to first page
            window.location.href = currentUrl.toString();
        }
        
        function filterQuestions() {
            const searchTerm = searchInput.value.toLowerCase().trim();
            let visibleCount = 0;
            
            allQuestions.forEach(card => {
                const questionStem = card.getAttribute('data-question-stem') || '';
                const questionId = card.getAttribute('data-question-id') || '';
                const questionType = card.getAttribute('data-question-type') || '';
                
                // Check search match
                const searchMatch = !searchTerm || 
                    questionStem.includes(searchTerm) || 
                    questionId.includes(searchTerm);
                
                // Check filter match
                const filterMatch = currentFilter === 'all' || questionType === currentFilter;
                
                const shouldShow = searchMatch && filterMatch;
                card.style.display = shouldShow ? 'block' : 'none';
                
                if (shouldShow) visibleCount++;
            });
            
            // Update count
            if (filteredCount) {
                filteredCount.textContent = visibleCount;
            }
            
            // Show/hide empty state
            if (emptySearch) {
                emptySearch.style.display = visibleCount === 0 && searchTerm ? 'flex' : 'none';
            }
            if (questionsList) {
                questionsList.style.display = visibleCount === 0 && searchTerm ? 'none' : 'flex';
            }
        }
        
        // Search input events with URL navigation
        searchInput.addEventListener('input', function() {
            const hasValue = this.value.trim().length > 0;
            searchClear.style.display = hasValue ? 'block' : 'none';
            
            // Debounce search
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                const searchTerm = this.value.trim();
                const currentUrl = new URL(window.location);
                if (searchTerm) {
                    currentUrl.searchParams.set('search', searchTerm);
                } else {
                    currentUrl.searchParams.delete('search');
                }
                currentUrl.searchParams.delete('page'); // Reset to first page
                window.location.href = currentUrl.toString();
            }, 500);
        });
        
        // Clear search
        if (searchClear) {
            searchClear.addEventListener('click', function() {
                const currentUrl = new URL(window.location);
                currentUrl.searchParams.delete('search');
                currentUrl.searchParams.delete('page');
                window.location.href = currentUrl.toString();
            });
        }
        
        // Filter chip clicks
        document.querySelectorAll('.filter-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                setFilter(chip.dataset.filter);
            });
        });
    }
    
    // Auto-expand if coming from a specific question link
    const urlParams = new URLSearchParams(window.location.search);
    const expandQuestionId = urlParams.get('expand');
    if (expandQuestionId) {
        // Desktop
        const questionItem = document.querySelector(`[data-question-id="${expandQuestionId}"]`);
        if (questionItem) {
            const toggleButton = questionItem.querySelector('.toggle-expand');
            if (toggleButton) {
                toggleButton.click();
                questionItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
        
        // Mobile
        const mobileCard = document.querySelector(`.mobile-question-card[data-question-id="${expandQuestionId}"]`);
        if (mobileCard) {
            toggleMobileExpand(mobileCard);
            mobileCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
});