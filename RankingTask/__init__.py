from time import time

import itertools

import numpy as np
from otree.api import *

import json
with open('./RankingTask/tasks_info.json') as f:
    tasks_info = json.load(f)

doc = """
Ranking Task: Preliminary Survey
"""
rng = np.random.default_rng()

class C(BaseConstants):
    NAME_IN_URL = 'RankingTask'
    PLAYERS_PER_GROUP = None
    TASKS_INFO = tasks_info 
    NUM_PAIRS = 21
    NUM_ROUNDS = 11 + (2 + NUM_PAIRS) * len(TASKS_INFO) + 2 # instruction + task + result = 151

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    informed_consent = models.CharField(
        initial = None,
        choices = ['私は、以上の説明を理解したうえで、本調査に参加することに同意します。'],
        widget = widgets.RadioSelect()
        )
    id_number = models.IntegerField(
        initial = None,
        verbose_name = 'あなたのID番号を入力してください。'
        )
    gender = models.CharField(
        initial = None,
        choices = ['男性', '女性', '回答しない'],
        verbose_name = 'あなたの性別を教えてください。',
        widget = widgets.RadioSelect()
        )
    age = models.IntegerField(
        initial = None,
        verbose_name = 'あなたの年齢を教えてください。'
        )
    
    ranking_task = models.LongStringField()
    
    confidence = models.CharField(
        initial = None,
        choices = ['きわめて自信がある','かなり自信がある', '自信がある', 'あまり自信がない','ほとんど自信がない'],
        verbose_name = 'どの程度自信がありますか？',
        widget = widgets.RadioSelect()
    )

# FUNCTION
def creating_session(subsession: Subsession):
    if subsession.round_number == 1:
        for p in subsession.get_players():
            task_data = []
            question_id = 1
            for task in C.TASKS_INFO:
                task_id = task['task']
                task_kind = task['kind']
                question = task['question']
                candidates = task['candidate']
                rankings = task['ranking']
                for subquestion_id, (option1, option2) in enumerate(itertools.combinations(candidates, 2), start=1):
                    rank1 = rankings[candidates.index(option1)]
                    rank2 = rankings[candidates.index(option2)]
                    task_data.append({
                        'question_id': question_id,
                        'task_id': task_id,
                        'kind': task_kind,
                        'question': question,
                        'subquestion_id': subquestion_id,
                        'option1': option1,
                        'option2': option2,
                        'rank1': rank1,
                        'rank2': rank2
                    })
                    question_id += 1  
            p.participant.vars['all_tasks'] = task_data

            task_order = list(set([item['kind'] for item in task_data]))
            rng.shuffle(task_order)
            
            randomized_task_data = []
            for kind in task_order:
                task_questions = [q for q in task_data if q['kind'] == kind]
                rng.shuffle(task_questions)
                for question in task_questions:
                    if rng.random() < 0.5:
                        question['option1'], question['option2'] = question['option2'], question['option1']
                        question['rank1'], question['rank2'] = question['rank2'], question['rank1']
                randomized_task_data.extend(task_questions)
            for answer_order_id, question in enumerate(randomized_task_data, start=1):
                question['answer_order_id'] = answer_order_id
            p.participant.vars['randomized_tasks'] = randomized_task_data
            print(task_order)


# PAGES
class InformedConsent(Page):
    form_model = 'player'
    form_fields = ['informed_consent']

    def is_displayed(player):
        return player.round_number == 1
    
    def error_message(player, value):
        if not value.get('informed_consent'):
            return '回答を選択してください。'
    
    def before_next_page(player, timeout_happened):
        player.participant.vars['informed_consent'] = player.informed_consent


class Demographic(Page):
    form_model = 'player'
    form_fields = ['id_number', 'gender', 'age']

    @staticmethod
    def is_displayed(player):
        return player.round_number == 2
    
    def error_message(player, value):
        if not value.get('id_number'):
            return '回答を記入してください。'
        if not value.get('gender'):
            return '回答を選択してください。'
        if not value.get('age'):
            return '回答を記入してください。'
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.participant.vars['id_number'] = player.id_number
        player.participant.vars['gender'] = player.gender
        player.participant.vars['age'] = player.age

class PreInstruction1(Page):
    form_model = 'player'

    @staticmethod
    def is_displayed(player):
        return player.round_number == 3

class PreInstruction2(Page):
    form_model = 'player'

    @staticmethod
    def is_displayed(player):
        return player.round_number == 4

class PreInstruction3(Page):
    form_model = 'player'

    @staticmethod
    def is_displayed(player):
        return 5 <= player.round_number <= 10
    
    @staticmethod
    def vars_for_template(player):
        task_index = player.round_number - 5
        task_info = C.TASKS_INFO[task_index]
        
        return {
            'kind_number': task_index + 1,
            'kind': task_info['kind'],
            'question': task_info['question'],
            'example1': task_info['example'][0],
            'example2': task_info['example'][1],
            'annotations': task_info['annotation'],
            'instruction': task_info['instruction'][0]
        }

class PreInstruction4(Page):
    form_model = 'player'

    def is_displayed(player):
        return player.round_number == 11


class Announce(Page):
    @staticmethod
    def is_displayed(player: Player):
        task_set_start_rounds = [12 + i * (C.NUM_PAIRS + 2) for i in range(len(C.TASKS_INFO))]
        return player.round_number in task_set_start_rounds

    @staticmethod
    def vars_for_template(player):
        task_index = (player.round_number - 12) // (C.NUM_PAIRS + 2)
        current_task = player.participant.vars['randomized_tasks'][task_index * C.NUM_PAIRS]['kind']

        return {
            'task_order': task_index + 1,
            'task_kind': current_task,
        }


class Instruction(Page):
    @staticmethod
    def is_displayed(player: Player):
        task_set_start_rounds = [12 + i * (C.NUM_PAIRS + 2) for i in range(len(C.TASKS_INFO))]
        instruction_rounds = [round + 1 for round in task_set_start_rounds]
        return player.round_number in instruction_rounds

    @staticmethod
    def vars_for_template(player):
        task_index = (player.round_number - 12) // (C.NUM_PAIRS + 2)
        current_task = player.participant.vars['randomized_tasks'][task_index * C.NUM_PAIRS]['kind']
        current_task_info = next(task for task in C.TASKS_INFO if task['kind'] == current_task)

        return {
            'question': current_task_info['question'],
            'example1': current_task_info['example'][0],
            'example2': current_task_info['example'][1],
            'annotations': current_task_info['annotation']
        }



class Task(Page):
    form_model = 'player'
    form_fields = ['ranking_task', 'confidence']

    @staticmethod
    def is_displayed(player: Player):
        task_set_start_rounds = [12 + i * (C.NUM_PAIRS + 2) for i in range(len(C.TASKS_INFO))]
        task_rounds = [round + j for round in task_set_start_rounds for j in range(2, 2 + C.NUM_PAIRS)]
        return player.round_number in task_rounds

    @staticmethod
    def vars_for_template(player):
        player.participant.vars['start_time'] = time()
        
        task_cycle_length = 2 + C.NUM_PAIRS
        task_index = (player.round_number - 12) // task_cycle_length
        offset = 14 + task_index * 2
        current_question_index = player.round_number - offset
        current_question = player.participant.vars['randomized_tasks'][current_question_index]
        
        current_kind = current_question['kind']
        pair_num = sum(1 for q in player.participant.vars['randomized_tasks'][:current_question_index] if q['kind'] == current_kind) + 1
        
        return {
            'pair_num': pair_num,
            'answer_order_id': current_question['answer_order_id'],
            'question_id': current_question['question_id'],
            'task_id': current_question['task_id'],
            'kind': current_question['kind'],
            'question': current_question['question'],
            'subquestion_id': current_question['subquestion_id'],
            'option1': current_question['option1'],
            'option2': current_question['option2'],
            'confidence_question': 'その判断に自信がありますか？',
            'confidence_choices': ['きわめて自信がある', 'かなり自信がある', '自信がある', 'あまり自信がない', 'ほとんど自信がない']
        }
    
        def error_message(player, value):
            if not value.get('ranking_task'):
                return '回答を選択してください。'
    
    @staticmethod
    def before_next_page(player, timeout_happened):
        task_cycle_length = 2 + C.NUM_PAIRS
        task_index = (player.round_number - 12) // task_cycle_length
        offset = 14 + task_index * 2
        current_question_index = player.round_number - offset
        
        start_time = player.participant.vars.get('start_time')
        if start_time:
            elapsed_time = time() - start_time
            player.participant.vars[f'elapsed_time_{current_question_index}'] = elapsed_time
        
        current_question = player.participant.vars['randomized_tasks'][current_question_index]
        answer = player.ranking_task
        true_false = None

        if answer == current_question['option1']:
            true_false = 1 if current_question['rank1'] < current_question['rank2'] else 0
        elif answer == current_question['option2']:
            true_false = 1 if current_question['rank2'] < current_question['rank1'] else 0
            
        confidence = player.confidence
        confidence_num = None
        
        if confidence == 'きわめて自信がある':
            confidence_num = 5
        elif confidence == 'かなり自信がある':
            confidence_num = 4
        elif confidence == '自信がある':
            confidence_num = 3
        elif confidence == 'あまり自信がない':
            confidence_num = 2
        elif confidence == 'ほとんど自信がない':
            confidence_num = 1
        
        player.participant.vars[f'answer_{current_question_index}'] = {
            'question_id': current_question['question_id'],
            'answer': answer,
            'true_false': true_false,
            'confidence': confidence,
            'confidence_num': confidence_num,
            'time_spent': elapsed_time
        }


class Answer(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == C.NUM_ROUNDS - 1
    
    @staticmethod
    def vars_for_template(player):
        task_answers = []
        for task_index, task in enumerate(C.TASKS_INFO):
            kind = task['kind']
            
            start_index = task_index * C.NUM_PAIRS
            end_index = start_index + C.NUM_PAIRS
            correct_count = sum(
                1 for idx in range(start_index, end_index)
                if player.participant.vars.get(f'answer_{idx}', {}).get('true_false') == 1
            )
            
            total_questions = C.NUM_PAIRS
            
            task_answers.append({
                'kind': kind,
                'correct_count': correct_count,
                'total_questions': total_questions,
                'candidates': task['candidate']
            })
        
        return {
            'task_answers': task_answers
        }


class Results(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == C.NUM_ROUNDS


page_sequence = [
    InformedConsent, Demographic,
    PreInstruction1, PreInstruction2, PreInstruction3, PreInstruction4,
    Announce, Instruction, Task,
    Answer, Results
]


def custom_export(players):
    yield [
        'participant_code', 'session_code', 'time_started_utc',
        'ID', 'informed_consent', 'gender', 'age',
        'answer_order_id','questionID', 'task_id', 'kind', 'subquestionID', 
        'option1', 'option2', 'rank1', 'rank2',
        'answer', 'true_false', 'confidence', 'confidence_num', 'time_spent'
    ]
    for player in players:
        if player.round_number == C.NUM_ROUNDS:
            for idx, task in enumerate(player.participant.vars['randomized_tasks']):
                answer_data = player.participant.vars.get(f'answer_{idx}', {})
                elapsed_time = player.participant.vars.get(f'elapsed_time_{idx}', {})
                yield [
                    player.participant.code,
                    player.session.code,
                    player.participant.time_started_utc,
                    player.participant.vars.get('id_number'),
                    player.participant.vars.get('informed_consent'),
                    player.participant.vars.get('gender'),
                    player.participant.vars.get('age'),
                    task['answer_order_id'],
                    task['question_id'],
                    task['task_id'],
                    task['kind'],
                    task['subquestion_id'],
                    task['option1'],
                    task['option2'],
                    task['rank1'],
                    task['rank2'],
                    answer_data.get('answer'),
                    answer_data.get('true_false'),
                    answer_data.get('confidence'),
                    answer_data.get('confidence_num'),
                    elapsed_time
                ]