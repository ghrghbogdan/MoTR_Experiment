<template>
  <Experiment title="Mouse tracking for Reading" translate="no">

    <Screen :title="'Welcome'" class="instructions" :validations="{
        SubjectID: {
          minLength: $magpie.v.minLength(2)
        }
      }">
      <div style="width: 40em; margin: auto;">

        <div style="background-color: lightgrey; padding: 10px;">
          <b> Information About this Study </b>
        </div>
        <p>
          We would like to ask you if you are willing to participate in our research project. Your participation is voluntary. Please read the text below carefully and ask the conducting person about anything you do not understand or would like to know.
          <br><br>
          <b>What is investigated and how?</b> You are being asked to take part in a research study being done by Gheorghe Bogdan & Nisioi Sergiu.

        </p>

        <br>
        <div style="background-color: lightgrey; padding: 10px;">
          <b> Consent Form </b>
        </div>
        <br>
        I, the participant, confirm by clicking the button below: <br>
        <div style="padding-left: 30px"> • I have read and understood the study information... </div>
        <div style="padding-left: 30px">• I comply with the inclusion and exclusion criteria... </div>
        <div style="padding-left: 30px">• I have had enough time to decide about my participation. </div>
        <div style="padding-left: 30px">• I participate in this study voluntarily...</div>
        <div style="padding-left: 30px">• I understand that I can stop participating at any moment.</div>
        <br>

        <table>
          <tbody>
            <tr>
              <td>Please enter your Prolific ID to continue:&nbsp;</td>
              <td><input name="TurkID" type="text" class="obligatory" v-model="$magpie.measurements.SubjectID" /></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="$magpie.measurements.SubjectID && !$magpie.validateMeasurements.SubjectID.$invalid">
        <br> By clicking on the button below you consent to participating in this study: <br><br>
        <br />
        <button @click="$magpie.addExpData({ SubjectId: $magpie.measurements.SubjectID}); $magpie.nextScreen()">
          Proceed
        </button>
      </div>
    </Screen>


    <InstructionScreen :title="'Instruction'">
      <p>In this study, you will read short texts and answer questions about them. However, unlike in normal reading, the texts will be blurred. In order to bring the text into focus move your mouse over it.</p>
      <p><strong>Important:</strong> At the beginning of each line, hover the small blue box to start reading that line. At the end of the line, hover the blue box to finish.</p>
      <p><strong>Tip:</strong> If you need to re-read previous lines, hold down the mouse button and move freely across the text. When you release the button, reading will continue normally on the line where you stopped.</p>
      <p>Take as much time to read the text as you need in order to understand it. When you are done reading, answer the question at the bottom and click "next" to move on.</p>
    </InstructionScreen>

    <template v-for="(trial, i) of trials">
      <Screen v-if="i > 0 && i < trials.length" 
              :key="'break-' + i"
              :progress="i / trials.length">
        <div style="text-align: center; padding: 60px 40px;">
          <p style="font-size: 18px; margin-bottom: 30px;">
            Take a break.
          </p>
          <button @click="$magpie.nextScreen()" 
                  style="padding: 12px 30px; font-size: 16px; background-color: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; position: static; transform: none; left: auto;">
            Next
          </button>
        </div>
      </Screen>

      <Screen :key="'trial-' + i" class="main_screen" :progress="i / trials.length" @next="currentIndex = i; currentPage = 0; currentQuestionIndex = 0; showQuestions = false">
        <Slide>
          <form>
            <input type="hidden" class="item_id" :value="trial.ItemId">
            <input type="hidden" class="experiment_id" :value="trial.Experiment">
            <input type="hidden" class="condition_id" :value="trial.Condition">
          </form>
          <div class="oval-cursor"></div>
          <template>
            <div v-if="!showQuestions" class="readingText" :id="'trial-' + i" @mousemove="moveCursor" @mouseleave="changeBack">
              <span v-for="(word, index) of (trial.pages && trial.pages[currentPage] ? trial.pages[currentPage].replace(/\n+/g, ' ') : '').split(' ')" :key="index" :data-index="index" class="word-span">
                {{ word }}
              </span>
            </div>
            <div v-if="!showQuestions" class="blurry-layer" style="opacity: 0.5; filter: blur(8px); transition: all 0.3s linear 0s;">
              <span v-for="(word, index) of (trial.pages && trial.pages[currentPage] ? trial.pages[currentPage].replace(/\n+/g, ' ') : '').split(' ')" :key="index" class="word-span">
                {{ word }}
              </span>
            </div>
          </template>
          
          <!-- Pagination Controls -->
          <div v-if="!showQuestions" style="position: absolute; bottom: 30px; left: 0; width: 100%; display: flex; justify-content: flex-end; padding-right: 80px; box-sizing: border-box; pointer-events: none; z-index: 10;">
            
            <button v-if="currentPage < trial.totalPages - 1" @click="nextPage(trial, i)" 
                    style="pointer-events: auto; position: relative; left: auto; transform: none; margin: 0; padding: 12px 24px; font-size: 15px; background-color: #2196F3; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; box-shadow: 0 2px 4px rgba(0,0,0,0.2); transition: all 0.2s; width: 160px;">
              Next →
            </button>
            
            <button v-else @click="finishReading()" :disabled="!isCursorMoving" 
                    style="pointer-events: auto; position: relative; left: auto; transform: none; margin: 0; padding: 12px 24px; font-size: 15px; background-color: #4CAF50; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; box-shadow: 0 2px 4px rgba(0,0,0,0.2); transition: all 0.2s; width: 160px;"
                    :style="!isCursorMoving ? 'opacity: 0.5; cursor: not-allowed;' : ''">
              Done Reading
            </button>

          </div>

          <!-- Questions Section -->
          <template v-if="showQuestions">
            
            <div style="position:absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; width: 90%; max-width: 800px; z-index: 15;">
              <div v-if="currentQuestionIndex < trial.questions.length">
                <div style="font-size: 20px; margin-bottom: 15px; font-weight: bold;">Question {{ currentQuestionIndex + 1 }} / {{ trial.questions.length }}</div>
                <div style="font-size: 18px; margin-bottom: 25px;">{{ trial.questions[currentQuestionIndex].question }}</div>
                
                <div style="display: flex; flex-direction: column; gap: 12px; max-width: 600px; margin: 0 auto;">
                  <label v-for='(option, idx) of trial.questions[currentQuestionIndex].options' :key="idx" 
                         style="display: flex; align-items: center; padding: 14px; border: 2px solid #ddd; border-radius: 8px; cursor: pointer; transition: all 0.2s;" 
                         :style="trial.questions[currentQuestionIndex].userResponse === option ? 'background-color: #e3f2fd; border-color: #2196f3;' : ''"
                         @click="trial.questions[currentQuestionIndex].userResponse = option">
                    <input :id="'q'+currentQuestionIndex+'_opt_'+idx" type="radio" :value="option" 
                           :name="'question_'+currentQuestionIndex" 
                           v-model="trial.questions[currentQuestionIndex].userResponse" 
                           style="margin-right: 12px;" />
                    <span style="flex: 1; text-align: left;">{{ option }}</span>
                  </label>
                </div>
              </div>
            </div>

            <div style="position: absolute; bottom: 30px; left: 0; width: 100%; display: flex; justify-content: flex-end; padding-right: 80px; box-sizing: border-box; pointer-events: none; z-index: 20;">
                <div v-if="currentQuestionIndex < trial.questions.length">
                  <button v-if="trial.questions[currentQuestionIndex].userResponse" 
                          @click="submitAnswer(trial)" 
                          style="pointer-events: auto; position: relative; left: auto; bottom: auto; transform: none; margin: 0; padding: 14px 40px; font-size: 16px; background-color: #4CAF50; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; box-shadow: 0 2px 4px rgba(0,0,0,0.2); transition: all 0.2s;">
                    {{ currentQuestionIndex < trial.questions.length - 1 ? 'Next Question' : 'Submit All Answers' }}
                  </button>
                </div>
            </div>

          </template>
        </Slide>
      </Screen>
    </template>

    <!-- Questionnaire Screen 1: Demographics -->
    <Screen :title="'Chestionar - Partea 1'">
      <div style="width: 50em; margin: auto; text-align: left;">
        <h3 style="text-align: center; margin-bottom: 20px;">Date demografice</h3>
        
        <p><strong>1. Gen</strong></p>
        <MultipleChoiceInput :response.sync="$magpie.measurements.gender" orientation="horizontal" 
          :options="['bărbat', 'femeie', 'altele', 'preferă să nu spună']" />
        <br>
        
        <p><strong>2. Vârsta</strong> <small>(în ani)</small></p>
        <TextareaInput :response.sync="$magpie.measurements.age" />
        <br>
        
        <p><strong>3. Ani de educație</strong> <small>(începând cu școala primară, excluzând grădinița)</small></p>
        <MultipleChoiceInput :response.sync="$magpie.measurements.years_education" orientation="horizontal" 
          :options="['1-5', '6-10', '11-15', '16-20', '>20 de ani']" />
        <br>
        
        <p><strong>4. Cel mai înalt nivel de educație absolvit</strong></p>
        <MultipleChoiceInput :response.sync="$magpie.measurements.level_education" orientation="vertical" 
          :options="['Învățământ primar', 'Învățământ secundar inferior', 'Învățământ secundar superior', 'Învățământ postliceal non-terțiar', 'Învățământ terțiar cu ciclu scurt', 'Diplomă de licență sau echivalentă', 'Masterat sau echivalent', 'Doctorat sau echivalent']" />
        <br>
        
        <p><strong>5. Comparativ cu alte persoane din comunitatea dvs., cum vă apreciați statutul socio-economic?</strong></p>
        <MultipleChoiceInput :response.sync="$magpie.measurements.socio_economic_status" orientation="horizontal" 
          :options="['sub medie', 'medie', 'peste medie', 'prefer să nu spun']" />
        
        <br><br>
        <button @click="$magpie.saveAndNextScreen();">Continuă →</button>
      </div>
    </Screen>

    <!-- Questionnaire Screen 2: Language Background -->
    <Screen :title="'Chestionar - Partea 2'">
      <div style="width: 50em; margin: auto; text-align: left;">
        <h3 style="text-align: center; margin-bottom: 20px;">Istoric lingvistic</h3>
        
        <p><strong>6. În copilărie, ați crescut vorbind una sau mai multe limbi în același timp?</strong></p>
        <small>Fără a lua în considerare limbile învățate în școală sau la cursuri.</small>
        <MultipleChoiceInput :response.sync="$magpie.measurements.childhood_languages" orientation="horizontal" 
          :options="['o singură limbă', 'două limbi', 'trei limbi']" />
        <br>
        
        <p><strong>7. Care este prima limbă pe care ați învățat-o în copilărie?</strong></p>
        <TextareaInput :response.sync="$magpie.measurements.native_language_1" />
        <br>
        
        <p><strong>8. Cu ce altă limbă (alte limbi) ați crescut?</strong> <small>(dacă este cazul)</small></p>
        <TextareaInput :response.sync="$magpie.measurements.native_language_other" />
        <br>
        
        <p><strong>9. Ce limbă folosiți cel mai mult în prezent?</strong></p>
        <TextareaInput :response.sync="$magpie.measurements.use_language" />
        <br>
        
        <p><strong>10. Care este limba cu care vă simțiți cel mai bine în prezent?</strong></p>
        <TextareaInput :response.sync="$magpie.measurements.dominant_language" />
        <br>
        
        <p><strong>11. Vorbiți un dialect sau o variantă specifică?</strong></p>
        <TextareaInput :response.sync="$magpie.measurements.dialect" />
        
        <br><br>
        <button @click="$magpie.saveAndNextScreen();">Continuă →</button>
      </div>
    </Screen>

    <!-- Questionnaire Screen 3: Reading Habits -->
    <Screen :title="'Chestionar - Partea 3'">
      <div style="width: 50em; margin: auto; text-align: left;">
        <h3 style="text-align: center; margin-bottom: 20px;">Obiceiuri de lectură</h3>
        <p><em>Într-o săptămână obișnuită, cât timp petreceți citind fiecare tip de material? (excluzând audiobook-urile)</em></p>
        
        <p><strong>12a. Materiale academice</strong></p>
        <MultipleChoiceInput :response.sync="$magpie.measurements.academic_reading_time" orientation="horizontal" 
          :options="['0 ore', 'mai puțin de 1 oră', '1-3 ore', '3-5 ore', 'mai mult de 5 ore']" />
        
        <p><strong>12b. Reviste</strong></p>
        <MultipleChoiceInput :response.sync="$magpie.measurements.magazine_reading_time" orientation="horizontal" 
          :options="['0 ore', 'mai puțin de 1 oră', '1-3 ore', '3-5 ore', 'mai mult de 5 ore']" />
        
        <p><strong>12c. Ziare</strong></p>
        <MultipleChoiceInput :response.sync="$magpie.measurements.newspaper_reading_time" orientation="horizontal" 
          :options="['0 ore', 'mai puțin de 1 oră', '1-3 ore', '3-5 ore', 'mai mult de 5 ore']" />
        
        <p><strong>12d. E-mail-uri</strong></p>
        <MultipleChoiceInput :response.sync="$magpie.measurements.email_reading_time" orientation="horizontal" 
          :options="['0 ore', 'mai puțin de 1 oră', '1-3 ore', '3-5 ore', 'mai mult de 5 ore']" />
        
        <p><strong>12e. Cărți de ficțiune</strong></p>
        <MultipleChoiceInput :response.sync="$magpie.measurements.fiction_reading_time" orientation="horizontal" 
          :options="['0 ore', 'mai puțin de 1 oră', '1-3 ore', '3-5 ore', 'mai mult de 5 ore']" />
        
        <p><strong>12f. Cărți de non-ficțiune</strong></p>
        <MultipleChoiceInput :response.sync="$magpie.measurements.nonfiction_reading_time" orientation="horizontal" 
          :options="['0 ore', 'mai puțin de 1 oră', '1-3 ore', '3-5 ore', 'mai mult de 5 ore']" />
        
        <p><strong>12g. Articole de pe internet (social media, forumuri, bloguri)</strong></p>
        <MultipleChoiceInput :response.sync="$magpie.measurements.internet_reading_time" orientation="horizontal" 
          :options="['0 ore', 'mai puțin de 1 oră', '1-3 ore', '3-5 ore', 'mai mult de 5 ore']" />
        
        <p><strong>13. Citiți în altă limbă?</strong> <small>(specificați limba/limbile)</small></p>
        <TextareaInput :response.sync="$magpie.measurements.additional_read_language" />
        
        <br><br>
        <button @click="$magpie.saveAndNextScreen();">Continuă →</button>
      </div>
    </Screen>

    <!-- Questionnaire Screen 4: Experiment Conditions -->
    <Screen :title="'Chestionar - Partea 4'">
      <div style="width: 50em; margin: auto; text-align: left;">
        <h3 style="text-align: center; margin-bottom: 20px;">Condiții în timpul experimentului</h3>
        
        <p><strong>14. Ați purtat ochelari sau lentile de contact în timpul experimentului?</strong></p>
        <MultipleChoiceInput :response.sync="$magpie.measurements.eyewear" orientation="horizontal" 
          :options="['ochelari', 'lentile', 'nu']" />
        <br>
        
        <p><strong>15. Cât de obosit/ă sunteți în prezent?</strong></p>
        <MultipleChoiceInput :response.sync="$magpie.measurements.tiredness" orientation="vertical" 
          :options="['1 - extrem de alert/ă', '2 - foarte alert/ă', '3 - alert/ă', '4 - destul de alert/ă', '5 - nici alert/ă, nici somnoros/ă', '6 - unele semne de somnolență', '7 - somnoros/ă, dar fără efort de a rămâne alert/ă', '8 - somnoros/ă, cu oarecare efort de a rămâne alert/ă', '9 - foarte somnoros/ă, efort mare de a rămâne alert/ă']" />
        <br>
        
        <p><strong>16. Ați consumat alcool ieri?</strong></p>
        <small>Datele vor fi anonimizate și tratate confidențial.</small>
        <MultipleChoiceInput :response.sync="$magpie.measurements.alcohol_yesterday" orientation="horizontal" 
          :options="['nu', 'da', 'prefer să nu răspund']" />
        <br>
        
        <p><strong>17. Ați consumat alcool astăzi?</strong></p>
        <MultipleChoiceInput :response.sync="$magpie.measurements.alcohol_today" orientation="horizontal" 
          :options="['nu', 'da', 'prefer să nu răspund']" />
        <br>
        
        <p><strong>18. Ce dispozitiv de intrare folosiți pentru acest experiment?</strong></p>
        <MultipleChoiceInput :response.sync="$magpie.measurements.device" orientation="horizontal" 
          :options="['Mouse', 'Trackpad', 'Altele']" />
        <br>
        
        <p><strong>19. Ce mână folosiți în timpul experimentului?</strong></p>
        <MultipleChoiceInput :response.sync="$magpie.measurements.hand" orientation="horizontal" 
          :options="['Stânga', 'Dreapta', 'Ambele']" />
        
        <br><br>
        <button @click="$magpie.saveAndNextScreen();">Trimite răspunsurile</button>
      </div>
    </Screen>

    <SubmitResultsScreen />
  </Experiment>
</template>

<script>

import ro_items from '../trials/ro_items.js';
import _ from 'lodash';

export default {
  name: 'App',
  data() {
    try {
      // Separate training item (ItemId: "0") from other items
      const trainingItem = ro_items.find(item => item.ItemId === "0");
      const experimentItems = ro_items.filter(item => item.ItemId !== "0");
      
      // Shuffle only the experiment items
      const shuffledExperimentItems = _.shuffle(experimentItems);
      
      // Put training item first, then shuffled experiment items
      const orderedItems = trainingItem ? [trainingItem, ...shuffledExperimentItems] : shuffledExperimentItems;
      
      const updatedTrials = orderedItems.map(trial => {
        
        const processedQuestions = trial.Questions.map(q => {
          const shuffledOptions = _.shuffle(q.options);
          return {
            ...q,
            options: shuffledOptions,
            userResponse: null
          };
        });
        
        return {
          ...trial,
          pages: trial.Pages,
          questions: processedQuestions,
          totalPages: trial.Pages.length
        }
      });
      
      return {
        isCursorMoving: false,
        trials: updatedTrials,
        currentIndex: null,
        currentLine: null,
        currentPage: 0,
        currentQuestionIndex: 0,
        showQuestions: false,
        isTrackingActive: false,
        isFreeReading: false,
        lineControls: [],
        lockedY: null,
        mousePosition: {
          x: 0,
          y: 0,
        },
        savingInterval: null,
      }
    } catch (error) {
      return {
        isCursorMoving: false,
        trials: [],
        currentIndex: null,
        currentLine: null,
        currentPage: 0,
        isTrackingActive: false,
        isFreeReading: false,
        lineControls: [],
        lockedY: null,
        showQuestions: false,
        mousePosition: {
          x: 0,
          y: 0,
        },
        savingInterval: null,
      }
    }
  },
  computed: {},
  mounted() {
    this.savingInterval = setInterval(this.saveData, 50);
    
    // Add global mouse event listeners for free reading mode
    document.addEventListener('mousedown', this.handleMouseDown);
    document.addEventListener('mouseup', this.handleMouseUp);
  },
  beforeDestroy() {
    if (this.savingInterval) {
      clearInterval(this.savingInterval);
    }
    
    // Remove event listeners
    document.removeEventListener('mousedown', this.handleMouseDown);
    document.removeEventListener('mouseup', this.handleMouseUp);
  },
  updated() {
    if (!this.showQuestions && this.lineControls.length === 0) {
      const readingText = document.querySelector('.readingText');
      if (readingText && readingText.children.length > 0) {
        this.$nextTick(() => {
          setTimeout(() => {
            this.calculateLineControls();
          }, 200);
        });
      }
    }
  },
  methods: {
    handleMouseDown(e) {
      const readingText = document.querySelector('.readingText');
      if (!readingText || this.showQuestions) return;
      
      // Check if click is inside reading text area
      const rect = readingText.getBoundingClientRect();
      if (e.clientX >= rect.left && e.clientX <= rect.right && 
          e.clientY >= rect.top && e.clientY <= rect.bottom) {
        this.isFreeReading = true;
        this.isTrackingActive = true;
        this.lockedY = null;
      }
    },
    handleMouseUp(e) {
      if (!this.isFreeReading) return;
      
      this.isFreeReading = false;
      
      // Re-lock Y position based on current cursor position
      const readingText = document.querySelector('.readingText');
      if (readingText) {
        const elementAtCursor = document.elementFromPoint(e.clientX, e.clientY);
        const wordSpan = elementAtCursor ? elementAtCursor.closest('span[data-index]') : null;
        
        if (wordSpan) {
          const wordIndex = parseInt(wordSpan.getAttribute('data-index'));
          
          // Find which line this word belongs to
          for (let lineIndex = 0; lineIndex < this.lineControls.length; lineIndex++) {
            if (this.lineControls[lineIndex].includes(wordIndex)) {
              this.currentLine = lineIndex;
              
              // Set locked Y to this line
              const rect = wordSpan.getBoundingClientRect();
              this.lockedY = rect.top + (rect.height / 2);
              
              // Update active box visual
              document.querySelectorAll('.line-box').forEach(box => {
                box.classList.remove('active');
                if (parseInt(box.dataset.line) === lineIndex) {
                  box.classList.add('active');
                }
              });
              
              break;
            }
          }
        }
      }
    },
    finishReading() {
      const allBoxes = document.querySelectorAll('.line-box');
      allBoxes.forEach(box => box.remove());
      
      this.showQuestions = true;
      this.currentQuestionIndex = 0;
      this.isCursorMoving = false;
      this.isTrackingActive = false;
      this.currentLine = null;
      this.lineControls = [];
    },
    submitAnswer(trial) {
      const currentQuestion = trial.questions[this.currentQuestionIndex];
      
      if (this.currentQuestionIndex < trial.questions.length - 1) {

        this.currentQuestionIndex++;
      } else {
        trial.questions.forEach((q, idx) => {
          this.$magpie.measurements[`question_${idx + 1}`] = q.question;
          this.$magpie.measurements[`answer_${idx + 1}`] = q.userResponse;
          this.$magpie.measurements[`correct_answer_${idx + 1}`] = q.correct_answer;
        });

        this.showQuestions = false;
        this.currentQuestionIndex = 0;
        this.currentPage = 0;
        
        this.$magpie.saveAndNextScreen();
      }
    },
    nextPage(trial, index) {
      this.currentIndex = index;
      if (this.currentPage < trial.totalPages - 1) {
        this.currentPage++;
        this.lineControls = [];
        this.isTrackingActive = false;
        this.currentLine = null;
        this.$nextTick(() => {
          setTimeout(() => {
            this.calculateLineControls();
          }, 200);
        });
      }
    },

    calculateLineControls() {
      const readingText = document.querySelector('.readingText');
      if (!readingText) {
        return;
      }

      const wordSpans = readingText.querySelectorAll('.word-span');
      if (wordSpans.length === 0) {
        return;
      }

      const lines = [];
      let currentTop = null;
      let lineWords = [];

      wordSpans.forEach((span, index) => {
        const rect = span.getBoundingClientRect();
        const parentRect = readingText.getBoundingClientRect();
        const relativeTop = Math.round(rect.top - parentRect.top);

        if (currentTop === null || Math.abs(relativeTop - currentTop) > 5) {
          if (lineWords.length > 0) {
            lines.push([...lineWords]);
          }
          currentTop = relativeTop;
          lineWords = [index];
        } else {
          lineWords.push(index);
        }
      });

      if (lineWords.length > 0) {
        lines.push(lineWords);
      }

      this.lineControls = lines;
      this.renderLineBoxes();
    },
    
    renderLineBoxes() {
      if (this.showQuestions) {
        return;
      }
      
      const readingText = document.querySelector('.readingText');
      if (!readingText) {
        return;
      }

      // Remove old boxes
      const oldBoxes = readingText.querySelectorAll('.line-box');
      oldBoxes.forEach(box => box.remove());

      let boxesCreated = 0;
      this.lineControls.forEach((lineWordIndices, lineIndex) => {
        const firstWord = readingText.querySelector(`[data-index="${lineWordIndices[0]}"]`);
        const lastWord = readingText.querySelector(`[data-index="${lineWordIndices[lineWordIndices.length - 1]}"]`);

        if (!firstWord || !lastWord) return;

        const parentRect = readingText.getBoundingClientRect();
        const firstRect = firstWord.getBoundingClientRect();
        const lastRect = lastWord.getBoundingClientRect();

        // Start box
        const startBox = document.createElement('div');
        startBox.className = 'line-box start-box';
        startBox.style.top = (firstRect.top - parentRect.top + (firstRect.height / 2) - 15) + 'px';
        startBox.style.left = (firstRect.left - parentRect.left - 30) + 'px';
        startBox.dataset.line = lineIndex;
        startBox.onmouseenter = () => this.activateLine(lineIndex);
        readingText.appendChild(startBox);

        // End box
        const endBox = document.createElement('div');
        endBox.className = 'line-box end-box';
        endBox.style.top = (lastRect.top - parentRect.top + (lastRect.height / 2) - 15) + 'px';
        endBox.style.left = (lastRect.right - parentRect.left + 15) + 'px';
        endBox.dataset.line = lineIndex;
        endBox.onmouseenter = () => this.deactivateLine(lineIndex);
        readingText.appendChild(endBox);
        
        boxesCreated++;
      });
    },
    activateLine(lineIndex) {
      this.currentLine = lineIndex;
      this.isTrackingActive = true;

      const readingText = document.querySelector('.readingText');
      if (readingText && this.lineControls[lineIndex]) {
        const firstWordIndex = this.lineControls[lineIndex][0];
        const firstWord = readingText.querySelector(`[data-index="${firstWordIndex}"]`);
        if (firstWord) {
          const rect = firstWord.getBoundingClientRect();
          this.lockedY = rect.top + (rect.height / 2);
        }
      }

      document.querySelectorAll('.line-box').forEach(box => {
        box.classList.remove('active');
        if (parseInt(box.dataset.line) === lineIndex) {
          box.classList.add('active');
        }
      });
    },
    deactivateLine(lineIndex) {
      if (this.currentLine === lineIndex) {
        this.isTrackingActive = false;
        this.currentLine = null;
        this.currentIndex = null;
        this.lockedY = null; 

        // Remove visual feedback
        document.querySelectorAll('.line-box').forEach(box => {
          box.classList.remove('active');
        });
      }
    },
    changeBack() {
      if (this.$el.querySelector(".oval-cursor")) {
        this.$el.querySelector(".oval-cursor").classList.remove('grow');
        this.$el.querySelector(".oval-cursor").classList.remove('blank');
      }
      this.currentIndex = null;
    },
    saveData() {
      if (!this.isTrackingActive) return;

      const responseTime = Date.now();

      if (this.currentIndex !== null) {
        const currentElement = this.$el.querySelector(`span[data-index="${this.currentIndex}"]`);
        if (currentElement) {
          const currentElementRect = currentElement.getBoundingClientRect();
          $magpie.addTrialData({
            responseTime: responseTime,
            Experiment: this.$el.querySelector(".experiment_id").value,
            Condition: this.$el.querySelector(".condition_id").value,
            ItemId: this.$el.querySelector(".item_id").value,
            Index: this.currentIndex,
            PageNumber: this.currentPage,
            Line: this.currentLine,
            Word: currentElement.innerHTML.replace(/[\r\n]+/g, ' ').trim(),
            mousePositionX: this.mousePosition.x,
            mousePositionY: this.mousePosition.y,
            wordPositionTop: currentElementRect.top,
            wordPositionLeft: currentElementRect.left,
            wordPositionBottom: currentElementRect.bottom,
            wordPositionRight: currentElementRect.right
          });
        }
      } else {
        $magpie.addTrialData({
          responseTime: responseTime,
          Experiment: this.$el.querySelector(".experiment_id").value,
          Condition: this.$el.querySelector(".condition_id").value,
          ItemId: this.$el.querySelector(".item_id").value,
          Index: this.currentIndex,
          PageNumber: this.currentPage,
          Line: this.currentLine,
          mousePositionX: this.mousePosition.x,
          mousePositionY: this.mousePosition.y,
        });

      }
    },
    moveCursor(e) {
      if (!this.isTrackingActive && !this.isFreeReading) {
        this.$el.querySelector(".oval-cursor").classList.remove('grow');
        this.$el.querySelector(".oval-cursor").classList.add('blank');
        return;
      }

      this.isCursorMoving = true;
      const cursor = this.$el.querySelector(".oval-cursor");
      cursor.classList.add('grow');

      let x = e.clientX;
      let y = this.isFreeReading ? e.clientY : (this.lockedY !== null ? this.lockedY : e.clientY);

      const elementAtCursor = document.elementFromPoint(x, y).closest('span');
      if (elementAtCursor) {
        cursor.classList.remove('blank');
        this.currentIndex = elementAtCursor.getAttribute('data-index');
      } else {
        cursor.classList.add('blank');
        const rawEl = document.elementFromPoint(x, y - 3);
        const elementAboveCursor = rawEl ? rawEl.closest('span') : null;
        
        if (elementAboveCursor) {
          this.currentIndex = elementAboveCursor.getAttribute('data-index');
        } else {
          this.currentIndex = -1;
        }
      }

      cursor.style.left = `${x + 12}px`;
      cursor.style.top = `${y - 6}px`;
      this.mousePosition.x = e.clientX;
      this.mousePosition.y = y;
    },
    getScreenDimensions() {
      return {
        window_inner_width: window.innerWidth,
        window_inner_height: window.innerHeight
      };
    }
  }, 
}; 
</script>

<style>
  @font-face {
    font-family: 'JetBrainsMono';
    src: url('/JetBrainsMono-Regular.ttf') format('truetype');
    font-weight: normal;
    font-style: normal;
  }
  
  .experiment {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 1340px !important;
    height: 1008px !important;
    border: 1px solid #ababab !important;
    border-radius: 10px !important;
    margin: 20px auto !important;
    padding: 0 !important;
    position: relative !important;
  }
  .main_screen {
    isolation: isolate;
    position: relative;
    width: 100%;
    height: auto;
    font-size: 18px;
    line-height: 40px;
  }
  .debugResults {
    width: 100%;
  }
  .readingText {
    /* z-index: 1; */
    position: absolute;
    color: white;
    text-align: left;
    font-family: 'JetBrainsMono', monospace;
    font-size: 23px;
    line-height: 2cm;
    font-weight: 450;
    cursor: pointer;
    padding: 2cm;
    width: 100%;
    height: 100%;
    box-sizing: border-box;
    word-wrap: break-word;
    overflow: hidden;
  }
  .word-span {
    margin-right: 0.3em;
  }
  .line-box {
    position: absolute;
    width: 12px;
    height: 30px;
    border: 2px solid #d1e3fa;
    border-radius: 3px;
    cursor: pointer;
    transition: all 0.2s ease;
    z-index: 5;
  }
  .line-box:hover {
    background-color: rgba(255, 255, 255, 0.6);
    box-shadow: 0 0 8px rgba(206, 228, 255, 0.2);
  }
  .line-box.active {
    background-color: rgba(255, 255, 255, 0.8);
    border-color: #bad7fc;
    border-width: 3px;
  }
  button {
    position: absolute;
    bottom: 0;
    left: 50%;
  }
  .oval-cursor {
    position: fixed;
    z-index: 2;
    width: 1px;
    height: 1px;
    transform: translate(-50%, -50%);
    background-color: white;
    mix-blend-mode: difference;
    border-radius: 50%;
    pointer-events: none;
    transition: width 0.5s, height 0.5s;
  }
  .oval-cursor.grow.blank {
    width: 80px;
    height: 13px;
  }
  .oval-cursor.grow {
    width: 102px;
    height: 38px;
    border-radius: 50%;
    box-shadow: 30px 0 8px -4px rgba(255, 255, 255, 0.1), -30px 0 8px -4px rgba(255, 255, 255, 0.1);
    background-color: rgba(255, 255, 255, 0.3);
    background-blend-mode: screen;
    pointer-events: none;
    transition: width 0.5s, height 0.5s;
    filter: blur(3px);
  }
  .oval-cursor.grow::before {
    content: "";
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 70%;
    height: 70%;
    background-color: white;
    mix-blend-mode: normal;
    border-radius: 50%;
  }
  .blurry-layer {
    position: absolute;
    pointer-events: none;
    color: black;
    text-align: left;
    font-family: 'JetBrainsMono', monospace;
    font-size: 23px;
    line-height: 2cm;
    font-weight: 450;
    padding: 2cm;
    width: 100%;
    height: 100%;
    box-sizing: border-box;
    word-wrap: break-word;
    overflow: hidden;
  }
  * {
    user-select: none;
    /* Standard syntax */
    -webkit-user-select: none;
    /* Safari */
    -moz-user-select: none;
    /* Firefox */
    -ms-user-select: none;
    /* Internet Explorer/Edge */
  }
</style>