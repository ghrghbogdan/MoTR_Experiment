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
          <b>What is investigated and how?</b> You are being asked to take part in a research study being done by Ethan Wilcox...
          <br><br>
          <b> General Contact: </b> Ethan Gotlieb Wilcox... <br>
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
      <p><strong>Important:</strong> At the beginning of each line, click the small blue box to start reading that line. At the end of the line, click the blue box to finish.</p>
      <p>Take as much time to read the text as you need in order to understand it. When you are done reading, answer the question at the bottom and click "next" to move on.</p>
    </InstructionScreen>

    <Screen v-for="(trial, i) of trials" :key="i" class="main_screen" :progress="i / trials.length" @next="currentIndex = i; currentPage = 0; currentQuestionIndex = 0; showQuestions = false">
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
            <div v-if="!showQuestions" class="blurry-layer" style="opacity: 0.3; filter: blur(3.5px); transition: all 0.3s linear 0s;">
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

    <Screen>
      <p>1. Which input device are you using for this experiment?</p>
      <MultipleChoiceInput :response.sync="$magpie.measurements.device" orientation="horizontal" :options="['Computer Mouse', 'Computer Trackpad', 'Other']" />
      <br>
      <br>
      <p>2. Which hand are you using during this experiment?</p>
      <MultipleChoiceInput :response.sync="$magpie.measurements.hand" orientation="horizontal" :options="['Left', 'Right', 'Both']" />
      <button style="bottom:30%; transform: translate(-50%, -50%)" @click="$magpie.saveAndNextScreen();">Submit</button>
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
      // shuffle texts
      const shuffledItems = _.shuffle(ro_items);
      
      const updatedTrials = shuffledItems.map(trial => {
        
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
  },
  beforeDestroy() {
    if (this.savingInterval) {
      clearInterval(this.savingInterval);
    }
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
          Line: this.currentLine,
          mousePositionX: this.mousePosition.x,
          mousePositionY: this.mousePosition.y,
        });

      }
    },
    moveCursor(e) {
      if (!this.isTrackingActive) {
        this.$el.querySelector(".oval-cursor").classList.remove('grow');
        this.$el.querySelector(".oval-cursor").classList.add('blank');
        return;
      }

      this.isCursorMoving = true;
      const cursor = this.$el.querySelector(".oval-cursor");
      cursor.classList.add('grow');

      let x = e.clientX;
      let y = this.lockedY !== null ? this.lockedY : e.clientY;

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
    border: 2px solid #4A90E2;
    border-radius: 3px;
    cursor: pointer;
    transition: all 0.2s ease;
    z-index: 5;
  }
  .line-box:hover {
    background-color: rgba(74, 144, 226, 0.4);
    box-shadow: 0 0 8px rgba(74, 144, 226, 0.6);
  }
  .line-box.active {
    background-color: rgba(74, 144, 226, 0.3);
    border-color: #2E6DB8;
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