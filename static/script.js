let currentQuestionIndex = 0;
let questions = [];
let studentAnswers = [];

// Fonction pour récupérer les QCMs depuis le serveur Flask
async function loadQuestions() {
    const response = await fetch('/qcms');
    questions = await response.json();
    displayQuestion();
}

// Fonction pour afficher la question actuelle
function displayQuestion() {
    const question = questions[currentQuestionIndex];
    if (!question) return;

    document.getElementById('question-text').innerText = question.question;

    const optionsContainer = document.getElementById('options-container');
    optionsContainer.innerHTML = ''; // Réinitialiser les options pour la nouvelle question

    document.getElementById('alert-container').style.display = 'none'; // Cacher l'alerte

    // Afficher les options avec des cases à cocher
    question.options.forEach((option, index) => {
        const optionLabel = document.createElement('label');
        const input = document.createElement('input');
        input.type = "checkbox";
        input.name = "option";
        input.value = option;

        // Ajouter un span pour le texte
        const span = document.createElement('span');
        span.innerText = option;

        input.addEventListener('change', function() {
            if (this.checked) {
                optionLabel.classList.add('selected');
                optionLabel.style.backgroundColor = '#007bff';  // Bleu lors de la sélection
                optionLabel.style.color = 'white';  // Texte blanc
            } else {
                optionLabel.classList.remove('selected');
                optionLabel.style.backgroundColor = '#f9f9f9';  // Couleur par défaut
                optionLabel.style.color = 'black';  // Texte noir
            }
        });

        optionLabel.appendChild(input);
        optionLabel.appendChild(span);
        optionsContainer.appendChild(optionLabel);
    });

    document.getElementById('correct-answer').style.display = 'none';
}

// Fonction pour passer à la question suivante
function nextQuestion() {
    const selectedOptions = document.querySelectorAll('input[name="option"]:checked');

    // Si des options sont cochées, on les enregistre
    if (selectedOptions.length > 0) {
        const answers = Array.from(selectedOptions).map(option => option.value);

        studentAnswers.push({
            id: questions[currentQuestionIndex].id,
            answer: answers
        });

        currentQuestionIndex++;

        if (currentQuestionIndex < questions.length) {
            displayQuestion();
        } else {
            submitAnswers();
        }
    } else {
        // Afficher l'indicateur d'alerte
        document.getElementById('alert-container').style.display = 'block';
    }
}

// Fonction pour afficher la réponse correcte sans perturber la sélection des cases
function showAnswer() {
    const correctAnswer = questions[currentQuestionIndex].correct_option;
    document.getElementById('correct-answer').style.display = 'block';
    document.getElementById('correct-answer').innerText = `La réponse correcte est : ${correctAnswer}`;
}

// Fonction pour soumettre les réponses au serveur Flask
async function submitAnswers() {
    const response = await fetch('/submit', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ answers: studentAnswers })
    });

    const result = await response.json();

    // Afficher le score final
    alert(`Votre score est de ${result.score}/${result.total_questions} (${result.percentage}%)`);
}

// Charger les questions dès que la page est prête
window.onload = loadQuestions;

// Event listeners pour les boutons "Voir la réponse" et "Question suivante"
document.getElementById('show-answer').addEventListener('click', showAnswer);
document.getElementById('next-question').addEventListener('click', nextQuestion);
