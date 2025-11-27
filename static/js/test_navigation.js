/**
 * Test Navigation System for Bank Exam Platform
 * Handles single-question navigation, section timing, and answer persistence
 */

class TestNavigator {
    constructor(testData) {
        this.testData = testData;
        this.currentQuestionIndex = 0;
        this.currentSectionIndex = 0;
        this.answers = {};
        this.markedForReview = new Set();
        this.sectionTimers = {};
        this.currentTimer = null;

        this.init();
    }

    init() {
        console.log('TestNavigator initialized', this.testData);
        this.renderQuestion();
        this.renderQuestionPalette();
        this.setupEventListeners();
        this.startSectionTimer();
    }

    setupEventListeners() {
        // Navigation buttons
        document.getElementById('prev-btn')?.addEventListener('click', () => this.previousQuestion());
        document.getElementById('next-btn')?.addEventListener('click', () => this.nextQuestion());
        document.getElementById('mark-review-btn')?.addEventListener('click', () => this.markForReview());
        document.getElementById('clear-response-btn')?.addEventListener('click', () => this.clearResponse());
        document.getElementById('submit-test-btn')?.addEventListener('click', () => this.submitTest());

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') {
                e.preventDefault();
                this.previousQuestion();
            } else if (e.key === 'ArrowRight') {
                e.preventDefault();
                this.nextQuestion();
            }
        });

        // Option selection
        document.querySelectorAll('input[name="answer"]').forEach(radio => {
            radio.addEventListener('change', (e) => this.saveAnswer(e.target.value));
        });
    }

    renderQuestion() {
        const question = this.getCurrentQuestion();
        console.log('Rendering question:', question);
        const questionContainer = document.getElementById('question-container');

        if (!question) {
            console.error('No question found for index', this.currentQuestionIndex);
            return;
        }

        // Show group context if exists
        let contextHTML = '';
        if (question.group_context_text) {
            // Check if context is JSON chart data
            let chartData = null;
            try {
                // Try to parse as JSON if it looks like JSON
                if (question.group_context_text.trim().startsWith('{')) {
                    chartData = JSON.parse(question.group_context_text);
                }
            } catch (e) {
                // Not JSON, treat as normal text
                console.log('Context is not JSON chart data');
            }

            if (chartData && chartData.type) {
                if (chartData.type === 'table') {
                    // Render Table
                    contextHTML = `
                        <div class="question-group-context mb-4 p-3 bg-light border rounded">
                            <h6 class="text-primary text-center mb-3">${question.group_title || chartData.title || 'Data Table'}</h6>
                            <div class="table-responsive">
                                <table class="table table-bordered table-striped table-hover text-center">
                                    <thead class="table-dark">
                                        <tr>
                                            ${(chartData.headers || []).map(h => `<th>${h}</th>`).join('')}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${(chartData.rows || []).map(row => `
                                            <tr>
                                                ${row.map(cell => `<td>${cell}</td>`).join('')}
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    `;
                } else {
                    // Render Chart (Bar, Line, Pie)
                    contextHTML = `
                        <div class="question-group-context mb-4 p-3 bg-light border rounded">
                            <h6 class="text-primary text-center mb-3">${question.group_title || chartData.title || 'Data Interpretation'}</h6>
                            <div style="position: relative; height: 300px; width: 100%;">
                                <canvas id="chart-${question.id}"></canvas>
                            </div>
                        </div>
                    `;
                    // We need to render the chart AFTER it's added to DOM
                    setTimeout(() => this.renderChart(`chart-${question.id}`, chartData), 100);
                }
            } else {
                // Normal text/image context
                contextHTML = `
                    <div class="question-group-context mb-4 p-3 bg-light border rounded">
                        <h6 class="text-primary">${question.group_title || 'Context'}</h6>
                        ${question.group_context_image ? `<img src="${question.group_context_image}" class="img-fluid mb-3" alt="Context diagram">` : ''}
                        <div class="context-text">${question.group_context_text}</div>
                    </div>
                `;
            }
        }

        questionContainer.innerHTML = `
            ${contextHTML}
            <div class="question-header mb-3">
                <span class="badge bg-primary">Question ${this.currentQuestionIndex + 1} of ${this.testData.questions.length}</span>
                <span class="badge bg-info ms-2">${question.section_name}</span>
            </div>
            <div class="question-text mb-4">
                <h5>${question.text}</h5>
            </div>
            <div class="options-list">
                ${this.renderOptions(question)}
            </div>
        `;

        // Re-attach event listeners for new options
        document.querySelectorAll('input[name="answer"]').forEach(radio => {
            radio.addEventListener('change', (e) => this.saveAnswer(e.target.value));
        });

        // Add click handlers for option containers to make the whole row clickable
        document.querySelectorAll('.option-container').forEach(container => {
            container.addEventListener('click', (e) => {
                // If clicked element is not the radio button itself (to avoid double toggle)
                if (e.target.type !== 'radio') {
                    const radio = container.querySelector('input[type="radio"]');
                    if (radio) {
                        radio.checked = true;
                        // Trigger change event manually since programmatic change doesn't fire it
                        radio.dispatchEvent(new Event('change'));
                    }
                }
            });
        });

        // Restore saved answer
        if (this.answers[question.id]) {
            const savedOption = document.querySelector(`input[value="${this.answers[question.id]}"]`);
            if (savedOption) savedOption.checked = true;
        }

        // Update navigation buttons
        this.updateNavigationButtons();
    }

    renderOptions(question) {
        const options = ['A', 'B', 'C', 'D'];
        if (question.option_e) options.push('E');

        return options.map(opt => `
            <div class="form-check mb-3 p-3 border rounded option-container position-relative hover-shadow" style="cursor: pointer; transition: all 0.2s;">
                <input class="form-check-input position-absolute" type="radio" name="answer" id="option_${opt}" value="${opt}" style="left: 1rem; top: 1.2rem;">
                <label class="form-check-label w-100 ps-4" for="option_${opt}" style="cursor: pointer;">
                    <strong>${opt})</strong> ${question[`option_${opt.toLowerCase()}`]}
                </label>
            </div>
        `).join('');
    }

    renderQuestionPalette() {
        const palette = document.getElementById('question-palette');
        const sections = this.groupQuestionsBySection();

        let paletteHTML = '';
        sections.forEach((questions, sectionName) => {
            paletteHTML += `
                <div class="section-palette mb-3">
                    <h6 class="text-muted small">${sectionName}</h6>
                    <div class="palette-grid">
                        ${questions.map((q, idx) => {
                const globalIdx = this.testData.questions.indexOf(q);
                const status = this.getQuestionStatus(q.id, globalIdx);
                return `
                                <button class="palette-btn ${status}" data-index="${globalIdx}">
                                    ${globalIdx + 1}
                                </button>
                            `;
            }).join('')}
                    </div>
                </div>
            `;
        });

        palette.innerHTML = paletteHTML;

        // Add click handlers
        document.querySelectorAll('.palette-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = parseInt(e.target.dataset.index);
                this.goToQuestion(index);
            });
        });
    }

    groupQuestionsBySection() {
        const sections = new Map();
        this.testData.questions.forEach(q => {
            if (!sections.has(q.section_name)) {
                sections.set(q.section_name, []);
            }
            sections.get(q.section_name).push(q);
        });
        return sections;
    }

    getQuestionStatus(questionId, index) {
        if (index === this.currentQuestionIndex) return 'current';
        if (this.markedForReview.has(questionId)) return 'marked';
        if (this.answers[questionId]) return 'answered';
        return 'not-visited';
    }

    getCurrentQuestion() {
        return this.testData.questions[this.currentQuestionIndex];
    }

    saveAnswer(value) {
        const question = this.getCurrentQuestion();
        this.answers[question.id] = value;
        this.renderQuestionPalette();
    }

    clearResponse() {
        const question = this.getCurrentQuestion();
        delete this.answers[question.id];
        document.querySelectorAll('input[name="answer"]').forEach(radio => {
            radio.checked = false;
        });
        this.renderQuestionPalette();
    }

    markForReview() {
        const question = this.getCurrentQuestion();
        if (this.markedForReview.has(question.id)) {
            this.markedForReview.delete(question.id);
        } else {
            this.markedForReview.add(question.id);
        }
        this.renderQuestionPalette();
    }

    previousQuestion() {
        if (this.currentQuestionIndex > 0) {
            this.currentQuestionIndex--;
            this.checkSectionChange();
            this.renderQuestion();
            this.renderQuestionPalette();
        }
    }

    nextQuestion() {
        if (this.currentQuestionIndex < this.testData.questions.length - 1) {
            this.currentQuestionIndex++;
            this.checkSectionChange();
            this.renderQuestion();
            this.renderQuestionPalette();
        }
    }

    goToQuestion(index) {
        if (index >= 0 && index < this.testData.questions.length) {
            this.currentQuestionIndex = index;
            this.checkSectionChange();
            this.renderQuestion();
            this.renderQuestionPalette();
        }
    }

    checkSectionChange() {
        const currentQuestion = this.getCurrentQuestion();
        const newSectionIndex = this.testData.sections.findIndex(s => s.name === currentQuestion.section_name);

        if (newSectionIndex !== this.currentSectionIndex) {
            this.currentSectionIndex = newSectionIndex;
            this.startSectionTimer();
        }
    }

    startSectionTimer() {
        // Clear existing timer
        if (this.currentTimer) {
            clearInterval(this.currentTimer);
        }

        const section = this.testData.sections[this.currentSectionIndex];
        if (!section) return;

        // Initialize section timer if not exists
        if (!this.sectionTimers[section.name]) {
            this.sectionTimers[section.name] = section.duration * 60; // Convert to seconds
        }

        const timerDisplay = document.getElementById('timer-display');
        const sectionNameDisplay = document.getElementById('current-section-name');

        if (sectionNameDisplay) {
            sectionNameDisplay.textContent = section.name;
        }

        this.currentTimer = setInterval(() => {
            this.sectionTimers[section.name]--;

            const minutes = Math.floor(this.sectionTimers[section.name] / 60);
            const seconds = this.sectionTimers[section.name] % 60;

            if (timerDisplay) {
                timerDisplay.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

                // Warning when less than 5 minutes
                if (this.sectionTimers[section.name] <= 300) {
                    timerDisplay.classList.add('text-danger');
                } else {
                    timerDisplay.classList.remove('text-danger');
                }
            }

            // Auto-transition to next section when time expires
            if (this.sectionTimers[section.name] <= 0) {
                clearInterval(this.currentTimer);
                this.handleSectionTimeout();
            }
        }, 1000);
    }

    handleSectionTimeout() {
        const nextSectionIndex = this.currentSectionIndex + 1;

        if (nextSectionIndex < this.testData.sections.length) {
            // Move to first question of next section
            const nextSection = this.testData.sections[nextSectionIndex];
            const firstQuestionOfNextSection = this.testData.questions.findIndex(q => q.section_name === nextSection.name);

            if (firstQuestionOfNextSection !== -1) {
                alert(`Time's up for ${this.testData.sections[this.currentSectionIndex].name}! Moving to ${nextSection.name}`);
                this.goToQuestion(firstQuestionOfNextSection);
            }
        } else {
            // All sections complete
            alert("Time's up! Submitting your test.");
            this.submitTest();
        }
    }

    updateNavigationButtons() {
        const prevBtn = document.getElementById('prev-btn');
        const nextBtn = document.getElementById('next-btn');

        if (prevBtn) {
            prevBtn.disabled = this.currentQuestionIndex === 0;
        }

        if (nextBtn) {
            if (this.currentQuestionIndex === this.testData.questions.length - 1) {
                nextBtn.textContent = 'Submit Test';
                nextBtn.classList.remove('btn-primary');
                nextBtn.classList.add('btn-success');
            } else {
                nextBtn.textContent = 'Next';
                nextBtn.classList.remove('btn-success');
                nextBtn.classList.add('btn-primary');
            }
        }
    }

    renderChart(canvasId, chartData) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        // Destroy existing chart instance if any (to prevent memory leaks/glitches)
        if (window.activeCharts && window.activeCharts[canvasId]) {
            window.activeCharts[canvasId].destroy();
        }
        if (!window.activeCharts) window.activeCharts = {};

        const config = {
            type: chartData.type,
            data: {
                labels: chartData.labels,
                datasets: chartData.datasets.map(ds => ({
                    ...ds,
                    backgroundColor: ds.backgroundColor || [
                        'rgba(54, 162, 235, 0.5)',
                        'rgba(255, 99, 132, 0.5)',
                        'rgba(255, 206, 86, 0.5)',
                        'rgba(75, 192, 192, 0.5)',
                        'rgba(153, 102, 255, 0.5)',
                    ],
                    borderColor: ds.borderColor || [
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 99, 132, 1)',
                        'rgba(255, 206, 86, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(153, 102, 255, 1)',
                    ],
                    borderWidth: 1
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: chartData.title
                    }
                }
            }
        };

        window.activeCharts[canvasId] = new Chart(ctx, config);
    }

    submitTest() {
        const answeredCount = Object.keys(this.answers).length;
        const totalQuestions = this.testData.questions.length;

        if (answeredCount < totalQuestions) {
            const unanswered = totalQuestions - answeredCount;
            if (!confirm(`You have ${unanswered} unanswered questions. Are you sure you want to submit?`)) {
                return;
            }
        }

        // Prepare form data
        const form = document.getElementById('test-form');

        // Add all answers to form
        Object.keys(this.answers).forEach(questionId => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = `question_${questionId}`;
            input.value = this.answers[questionId];
            form.appendChild(input);
        });

        // Submit the form
        form.submit();
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (window.testData) {
        window.testNavigator = new TestNavigator(window.testData);
    }
});
