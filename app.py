import streamlit as st
import streamlit.components.v1 as components
import sqlite3
from datetime import datetime, date, timedelta
import time
import json
import requests
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import math
import random

DB_PATH = "kaizen.db"

POINTS_PER_TASK = 10
LEVEL_STEP = 100
POMODORO_DURATION = 25 * 60

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

CLASS_INFO = {
    'warrior': {'name': 'Krieger',   'icon': '⚔️',  'bonus_desc': 'Highlight-Quests +25% XP',      'bonus_type': 'highlight', 'bonus_mult': 0.25, 'color': '#e74c3c',
                'bodies': {1:'🧍', 5:'⚔️', 15:'🥷', 25:'🛡️', 50:'🦸', 100:'🌋'}},
    'mage':    {'name': 'Magier',    'icon': '🧙',  'bonus_desc': 'Brain-Quests +25% XP',           'bonus_type': 'brain',     'bonus_mult': 0.25, 'color': '#9b59b6',
                'bodies': {1:'🧍', 5:'📚', 15:'🧙', 25:'🔮', 50:'✨', 100:'🌟'}},
    'scout':   {'name': 'Späher',    'icon': '🏃',  'bonus_desc': 'Schnelle Quests +35% XP',        'bonus_type': 'speed',     'bonus_mult': 0.35, 'color': '#27ae60',
                'bodies': {1:'🧍', 5:'🏃', 15:'🏹', 25:'🦅', 50:'⚡', 100:'🌪️'}},
    'engineer':{'name': 'Ingenieur', 'icon': '⚙️',  'bonus_desc': 'Habits & Micro-Quests +25% XP', 'bonus_type': 'micro',     'bonus_mult': 0.25, 'color': '#3498db',
                'bodies': {1:'🧍', 5:'🔧', 15:'⚙️', 25:'🤖', 50:'💻', 100:'🛸'}},
}

RARITY_COLORS = {'common':'#636e72','rare':'#00d4ff','epic':'#9b59b6','legendary':'#ffd700'}
RARITY_LABELS = {'common':'Gewöhnlich','rare':'Selten','epic':'Episch','legendary':'Legendär'}

# ─── Calisthenics Trainingssystem: Tracks & Progressionsstufen ────
CAL_TRACKS = {
    'push': {
        'label': 'Push', 'full_label': 'Push (Brust / Trizeps / Schulter)', 'icon': '💪', 'color': '#e74c3c',
        'levels': [
            {'name': 'Wand-Liegestütz',              'sets': 3, 'reps': 15, 'hold': False, 'cue': 'Hände schulterbreit an der Wand, Körper bildet eine gerade Linie.'},
            {'name': 'Knie-Liegestütz',               'sets': 3, 'reps': 12, 'hold': False, 'cue': 'Knie statt Füße als Stützpunkt, Rumpf bleibt fest.'},
            {'name': 'Liegestütz',                    'sets': 3, 'reps': 10, 'hold': False, 'cue': 'Volle Range of Motion, Brust fast bis zum Boden.'},
            {'name': 'Enge Liegestütz (Diamond)',     'sets': 3, 'reps': 8,  'hold': False, 'cue': 'Hände bilden ein Dreieck unter der Brust.'},
            {'name': 'Archer Liegestütz',             'sets': 3, 'reps': 6,  'hold': False, 'cue': 'Ein Arm gestreckt zur Seite, Gewicht auf dem anderen.'},
            {'name': 'Pseudo Planche Liegestütz',     'sets': 3, 'reps': 8,  'hold': False, 'cue': 'Hände auf Hüfthöhe, Schultern weit vor die Hände schieben.'},
            {'name': 'One-Arm Liegestütz (assistiert)','sets': 3, 'reps': 5, 'hold': False, 'cue': 'Andere Hand nur leicht zur Balance aufsetzen.'},
        ]
    },
    'pull': {
        'label': 'Pull', 'full_label': 'Pull (Rücken / Bizeps)', 'icon': '🪢', 'color': '#3498db',
        'levels': [
            {'name': 'Dead Hang',                     'sets': 3, 'reps': 20, 'hold': True,  'cue': 'Locker an der Stange hängen, Schultern aktiv nach unten ziehen.'},
            {'name': 'Negativer Klimmzug',             'sets': 3, 'reps': 5,  'hold': False, 'cue': 'Oben starten, so langsam wie möglich (5s) herunterlassen.'},
            {'name': 'Band-Klimmzug',                  'sets': 3, 'reps': 8,  'hold': False, 'cue': 'Resistance Band unter den Knien zur Unterstützung.'},
            {'name': 'Klimmzug',                       'sets': 3, 'reps': 6,  'hold': False, 'cue': 'Kinn über die Stange, volle Streckung unten.'},
            {'name': 'Enger Klimmzug (Chin-up)',       'sets': 3, 'reps': 8,  'hold': False, 'cue': 'Untergriff, eng, mehr Bizeps-Fokus.'},
            {'name': 'Archer Klimmzug',                'sets': 3, 'reps': 4,  'hold': False, 'cue': 'Ein Arm zieht aktiv, der andere bleibt fast gestreckt.'},
            {'name': 'One-Arm Klimmzug (assistiert)',  'sets': 3, 'reps': 3,  'hold': False, 'cue': 'Mit Band oder freier Hand am Handgelenk unterstützen.'},
        ]
    },
    'legs': {
        'label': 'Legs', 'full_label': 'Legs (Beine / Gesäß)', 'icon': '🦵', 'color': '#f39c12',
        'levels': [
            {'name': 'Kniebeuge',                     'sets': 3, 'reps': 15, 'hold': False, 'cue': 'Hüftbreit, Knie in Zehenrichtung, tief runter.'},
            {'name': 'Split Squat',                   'sets': 3, 'reps': 10, 'hold': False, 'cue': 'Ausfallschritt-Position, pro Bein zählen.'},
            {'name': 'Bulgarian Split Squat',         'sets': 3, 'reps': 10, 'hold': False, 'cue': 'Hinterer Fuß erhöht auf Stuhl oder Bank.'},
            {'name': 'Shrimp Squat (assistiert)',     'sets': 3, 'reps': 6,  'hold': False, 'cue': 'Hinteres Bein gebeugt halten, leicht abstützen.'},
            {'name': 'Pistol Squat (assistiert)',     'sets': 3, 'reps': 5,  'hold': False, 'cue': 'Mit Festhalten an Tür oder Geländer für Balance.'},
            {'name': 'Pistol Squat (frei)',           'sets': 3, 'reps': 5,  'hold': False, 'cue': 'Komplett frei, ein Bein gestreckt nach vorne.'},
        ]
    },
    'core': {
        'label': 'Core', 'full_label': 'Core (Rumpf)', 'icon': '🔥', 'color': '#9b59b6',
        'levels': [
            {'name': 'Plank',                         'sets': 3, 'reps': 40, 'hold': True,  'cue': 'Gerade Linie von Kopf bis Ferse, Bauch fest.'},
            {'name': 'Hollow Body Hold',               'sets': 3, 'reps': 25, 'hold': True,  'cue': 'Unterer Rücken fest am Boden, Arme/Beine leicht angehoben.'},
            {'name': 'Liegende Beinheber',             'sets': 3, 'reps': 12, 'hold': False, 'cue': 'Beine gestreckt heben, Rücken bleibt am Boden.'},
            {'name': 'Hängende Knieheber',             'sets': 3, 'reps': 10, 'hold': False, 'cue': 'An der Stange hängend, Knie zur Brust ziehen.'},
            {'name': 'Hängende Beinheber',             'sets': 3, 'reps': 10, 'hold': False, 'cue': 'Gestreckte Beine bis zur Waagerechten heben.'},
            {'name': 'Dragon Flag (negativ)',          'sets': 3, 'reps': 5,  'hold': False, 'cue': 'Oben starten, so kontrolliert wie möglich ablassen.'},
        ]
    },
    'skill_handstand': {
        'label': 'Handstand', 'full_label': 'Skill: Handstand', 'icon': '🤸', 'color': '#2ecc71',
        'levels': [
            {'name': 'Wand-Handstand (Bauch zur Wand)', 'sets': 3, 'reps': 20, 'hold': True, 'cue': 'Hände schulterbreit, in die Wand hineinlaufen.'},
            {'name': 'Wand-Handstand (Rücken zur Wand)','sets': 3, 'reps': 30, 'hold': True, 'cue': 'Schwieriger: Rücken zur Wand, Hüfte voll gestreckt.'},
            {'name': 'Wall Walk',                       'sets': 3, 'reps': 5,  'hold': False, 'cue': 'Aus der Plank rückwärts an der Wand hochlaufen.'},
            {'name': 'Freier Handstand-Versuch',        'sets': 3, 'reps': 10, 'hold': False, 'cue': 'Kick-up-Versuche in der Raummitte zählen.'},
            {'name': 'Freier Handstand Hold',           'sets': 3, 'reps': 10, 'hold': True,  'cue': 'Freistehend balancieren, Sekunden zählen.'},
        ]
    },
    'skill_muscleup': {
        'label': 'Muscle-up', 'full_label': 'Skill: Muscle-up', 'icon': '🚀', 'color': '#ffd700',
        'levels': [
            {'name': 'Explosive Klimmzüge',            'sets': 3, 'reps': 5,  'hold': False, 'cue': 'So hoch wie möglich ziehen, Brust Richtung Stange.'},
            {'name': 'Dips',                           'sets': 3, 'reps': 8,  'hold': False, 'cue': 'An Stange/Barren, Ellbogen eng, tief runter.'},
            {'name': 'Band-Muscle-up',                  'sets': 3, 'reps': 5,  'hold': False, 'cue': 'Mit Band unterstützt den Übergang üben.'},
            {'name': 'Negativer Muscle-up',             'sets': 3, 'reps': 5,  'hold': False, 'cue': 'Oben starten, langsam durch den Übergang absenken.'},
            {'name': 'Muscle-up',                       'sets': 3, 'reps': 3,  'hold': False, 'cue': 'Voller Übergang von Klimmzug zu Dip, sauber.'},
        ]
    },
}

# ─── Schlafrythmus & Abend-/Morgenroutine ─────────────────────────
EVENING_ROUTINE_TASKS = [
    {'key': 'phone_bed', 'icon': '📱', 'label': 'Handy ans Bett legen (Schlaf-Tracking starten)'},
    {'key': 'teeth',     'icon': '🦷', 'label': 'Zähne putzen'},
    {'key': 'shower',    'icon': '🚿', 'label': 'Duschen'},
    {'key': 'desk',      'icon': '🧹', 'label': 'Schreibtisch kurz aufräumen'},
    {'key': 'water_pm',  'icon': '💧', 'label': 'Glas Wasser ans Bett stellen'},
    {'key': 'mat_pm',    'icon': '🧘', 'label': '15 Min Chaktimatte / Faszientraining'},
]
MORNING_ROUTINE_TASKS = [
    {'key': 'water_am',  'icon': '💧', 'label': 'Glas Wasser trinken'},
    {'key': 'breakfast', 'icon': '🍳', 'label': 'Frühstücken'},
    {'key': 'mat_am',    'icon': '🧘', 'label': 'Chaktimatte / Faszientraining'},
    {'key': 'no_phone',  'icon': '📵', 'label': 'Erste Stunde kein Handy'},
]
SLEEP_RAMP_STEP_MINUTES = 10
SLEEP_GOAL_BEDTIME = "00:00"
SLEEP_GOAL_WAKETIME = "08:00"

# ─── Haushalt: wiederkehrende Aufgaben für ein Wohlfühl-Zuhause ───
HOUSEHOLD_TASKS = [
    # Täglich
    {'key': 'dishes',        'icon': '🍽️', 'label': 'Geschirr spülen / Spülmaschine ein-/ausräumen', 'frequency': 'daily',   'est_minutes': 10},
    {'key': 'kitchen_wipe',  'icon': '🧽', 'label': 'Küche kurz abwischen',                            'frequency': 'daily',   'est_minutes': 5},
    {'key': 'tidy_reset',    'icon': '🧹', 'label': '5-Minuten-Reset (kurz aufräumen)',                'frequency': 'daily',   'est_minutes': 5},
    {'key': 'trash_check',   'icon': '🗑️', 'label': 'Müll checken / rausbringen wenn voll',            'frequency': 'daily',   'est_minutes': 3},
    {'key': 'make_bed',      'icon': '🛏️', 'label': 'Bett machen',                                     'frequency': 'daily',   'est_minutes': 2},
    # Wöchentlich
    {'key': 'laundry',       'icon': '🧺', 'label': 'Wäsche waschen',                                  'frequency': 'weekly',  'est_minutes': 20},
    {'key': 'vacuum',        'icon': '🧹', 'label': 'Staubsaugen / Boden wischen',                     'frequency': 'weekly',  'est_minutes': 25},
    {'key': 'bathroom_clean','icon': '🚽', 'label': 'Bad putzen (Toilette, Dusche, Waschbecken)',      'frequency': 'weekly',  'est_minutes': 25},
    {'key': 'dust',          'icon': '🪶', 'label': 'Staub wischen',                                   'frequency': 'weekly',  'est_minutes': 15},
    {'key': 'groceries',     'icon': '🛒', 'label': 'Einkaufen (Lebensmittel)',                        'frequency': 'weekly',  'est_minutes': 45},
    {'key': 'plants',        'icon': '🪴', 'label': 'Pflanzen gießen',                                 'frequency': 'weekly',  'est_minutes': 5},
    {'key': 'sheets',        'icon': '🛌', 'label': 'Bettwäsche wechseln',                              'frequency': 'weekly',  'est_minutes': 15},
    # Monatlich
    {'key': 'fridge_clean',  'icon': '🧊', 'label': 'Kühlschrank reinigen & aussortieren',             'frequency': 'monthly', 'est_minutes': 20},
    {'key': 'windows',       'icon': '🪟', 'label': 'Fenster putzen',                                  'frequency': 'monthly', 'est_minutes': 30},
    {'key': 'oven_micro',    'icon': '🔥', 'label': 'Backofen / Mikrowelle reinigen',                  'frequency': 'monthly', 'est_minutes': 20},
    {'key': 'bathroom_deep', 'icon': '✨', 'label': 'Bad gründlich (Fugen, Kalk)',                      'frequency': 'monthly', 'est_minutes': 30},
    {'key': 'appliance_care','icon': '🌀', 'label': 'Wasch-/Spülmaschine pflegen (Filter, Pflegegang)','frequency': 'monthly', 'est_minutes': 15},
    {'key': 'declutter',     'icon': '📦', 'label': 'Schrank/Schublade ausmisten',                     'frequency': 'monthly', 'est_minutes': 25},
    {'key': 'smoke_detector','icon': '🔔', 'label': 'Rauchmelder testen',                              'frequency': 'monthly', 'est_minutes': 5},
]
HOUSEHOLD_FREQUENCY_DAYS = {'daily': 1, 'weekly': 7, 'monthly': 30}
HOUSEHOLD_FREQUENCY_LABELS = {'daily': '📅 Täglich', 'weekly': '🗓️ Wöchentlich', 'monthly': '📆 Monatlich'}

# ─── Season exclusive item keys (not shown in regular shop) ──────
SEASON_EXCLUSIVE_KEYS = {
    's1_aura_ocean','s1_aura_star','s1_aura_dawn','s1_aura_cosmic','s1_aura_rift',
    's1_aura_deep','s1_aura_beyond','s1_aura_legend','s1_aura_absolute',
    's1_body_rise','s1_body_guardian','s1_body_divine',
    's2_aura_void','s2_aura_night','s2_aura_shadow',
    's2_body_ghost','s2_body_shade',
    's3_aura_ember','s3_aura_hellfire',
    's3_body_fire','s3_body_demon',
}

SEASON_EXCLUSIVE_ITEMS = [
    # Season 1 auras
    ('s1_aura_ocean',   'Ozeantiefen-Aura',    'Exklusiv Season 1: Tiefe des Ozeans',       'cosmetic_aura','🌊',0,'epic',    'aura','ocean_s1',   1,0),
    ('s1_aura_star',    'Sternstunden-Aura',    'Exklusiv Season 1: Goldener Sternenglanz',  'cosmetic_aura','⭐',0,'epic',    'aura','star_s1',    1,0),
    ('s1_aura_dawn',    'Dämmerungsfeuer-Aura', 'Exklusiv Season 1: Flammen des Aufbruchs',  'cosmetic_aura','🌅',0,'epic',    'aura','dawn_s1',    1,0),
    ('s1_aura_cosmic',  'Kosmische Aura',       'Exklusiv Season 1: Kraft des Universums',   'cosmetic_aura','🌌',0,'epic',    'aura','cosmic_s1',  1,0),
    ('s1_aura_rift',    'Zeitriss-Aura',        'Exklusiv Season 1: Riss in der Realität',   'cosmetic_aura','💎',0,'legendary','aura','rift_s1',   1,0),
    ('s1_aura_deep',    'Tiefsee-Aura',         'Exklusiv Season 1: Abgrund des Meeres',     'cosmetic_aura','🌊',0,'epic',    'aura','deep_s1',    1,0),
    ('s1_aura_beyond',  'Jenseitiger Zyklus',   'Exklusiv Season 1: Jenseits der Zeit',      'cosmetic_aura','🔮',0,'legendary','aura','beyond_s1', 1,0),
    ('s1_aura_legend',  'Legendäre Krönung',    'Exklusiv Season 1: Krönung der Legende',    'cosmetic_aura','🌟',0,'legendary','aura','legend_s1', 1,0),
    ('s1_aura_absolute','Absolutes Bewusstsein','Exklusiv Season 1: Göttliches Licht',       'cosmetic_aura','✨',0,'legendary','aura','absolute_s1',1,0),
    ('s1_body_rise',    'Aufstiegs-Rüstung',    'Exklusiv Season 1: Rüstung des Aufstiegs',  'cosmetic_body','🛡️',0,'epic',   'body','rise',        1,0),
    ('s1_body_guardian','Hüter-Form',            'Exklusiv Season 1: Der ewige Hüter',        'cosmetic_body','🗡️',0,'legendary','body','guardian', 1,0),
    ('s1_body_divine',  'Göttliche Aufstiegs-Form','Exklusiv S1 Tier 50: Göttlichkeit',      'cosmetic_body','🌟',0,'legendary','body','divine_s1', 1,0),
    # Season 2 auras
    ('s2_aura_void',    'Leeren-Aura',          'Exklusiv Season 2: Das Nichts',             'cosmetic_aura','🕳️',0,'epic',    'aura','void_s2',   1,0),
    ('s2_aura_night',   'Nachtschwärmer-Aura',  'Exklusiv Season 2: Stille der Nacht',       'cosmetic_aura','🌙',0,'epic',    'aura','night_s2',   1,0),
    ('s2_aura_shadow',  'Schattenriss-Aura',    'Exklusiv Season 2: Grenzen des Schattens',  'cosmetic_aura','🌑',0,'legendary','aura','shadow_s2', 1,0),
    ('s2_body_ghost',   'Geisterform',          'Exklusiv Season 2: Zwischen den Welten',    'cosmetic_body','👻',0,'epic',   'body','ghost',        1,0),
    ('s2_body_shade',   'Schatten-Inkarnation', 'Exklusiv Season 2: Verkörperung des Schattens','cosmetic_body','🌑',0,'legendary','body','shade_s2',1,0),
    # Season 3 auras
    ('s3_aura_ember',   'Glutkern-Aura',        'Exklusiv Season 3: Glühende Energie',       'cosmetic_aura','🔥',0,'epic',    'aura','ember_s3',   1,0),
    ('s3_aura_hellfire','Höllenfeuer-Aura',     'Exklusiv Season 3: Feuer der Unterwelt',    'cosmetic_aura','🌋',0,'legendary','aura','hellfire_s3',1,0),
    ('s3_body_fire',    'Flammenreiter-Form',   'Exklusiv Season 3: Reiter der Flammen',     'cosmetic_body','🔥',0,'epic',   'body','fire_s3',      1,0),
    ('s3_body_demon',   'Dämonische Inkarnation','Exklusiv Season 3: Dämonen-Tier 50',       'cosmetic_body','😈',0,'legendary','body','demon_s3',  1,0),
]

def _build_season_pass_data():
    """Generates 3 season objects each with 50 tiers."""
    def _tiers(items_50):
        xp_thresholds = []
        cumxp = 0
        for i in range(50):
            if i < 10:   step = 200
            elif i < 20: step = 350
            elif i < 30: step = 550
            elif i < 40: step = 900
            else:        step = 1500
            cumxp += step
            xp_thresholds.append(cumxp)
        tiers = []
        for i, (xp, item) in enumerate(zip(xp_thresholds, items_50)):
            tiers.append({'tier': i+1, 'xp': xp, **item})
        return tiers

    S1 = [
        {'type':'title','icon':'🎖️','name':'Rekrut','value':'Rekrut'},
        {'type':'coins','icon':'🪙','name':'25 Münzen','value':'25'},
        {'type':'item', 'icon':'🌊','name':'Ozeantiefen-Aura','value':'s1_aura_ocean'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost','value':'xp_boost_24h'},
        {'type':'title','icon':'⬆️','name':'Aufsteiger','value':'Aufsteiger'},
        {'type':'coins','icon':'🪙','name':'40 Münzen','value':'40'},
        {'type':'item', 'icon':'⭐','name':'Sternstunden-Aura','value':'s1_aura_star'},
        {'type':'item', 'icon':'🛡️','name':'Streak-Schild','value':'streak_shield'},
        {'type':'coins','icon':'🪙','name':'60 Münzen','value':'60'},
        {'type':'item', 'icon':'🌅','name':'Dämmerungsfeuer-Aura','value':'s1_aura_dawn'},
        {'type':'title','icon':'🏅','name':'Veteran','value':'Veteran'},
        {'type':'coins','icon':'🪙','name':'80 Münzen','value':'80'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×2','value':'xp_boost_24h'},
        {'type':'item', 'icon':'🛡️','name':'Aufstiegs-Rüstung','value':'s1_body_rise'},
        {'type':'title','icon':'⚔️','name':'Kämpfer des Lichts','value':'Kämpfer des Lichts'},
        {'type':'coins','icon':'🪙','name':'100 Münzen','value':'100'},
        {'type':'item', 'icon':'🌌','name':'Kosmische Aura','value':'s1_aura_cosmic'},
        {'type':'item', 'icon':'💚','name':'Streak-Heiler','value':'streak_healer'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×2','value':'xp_boost_24h'},
        {'type':'item', 'icon':'💎','name':'Zeitriss-Aura','value':'s1_aura_rift'},
        {'type':'title','icon':'🌟','name':'Licht-Träger','value':'Licht-Träger'},
        {'type':'coins','icon':'🪙','name':'150 Münzen','value':'150'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×3','value':'xp_boost_24h'},
        {'type':'item', 'icon':'🛡️','name':'Streak-Schild ×2','value':'streak_shield'},
        {'type':'title','icon':'🔮','name':'Meister des Aufstiegs','value':'Meister des Aufstiegs'},
        {'type':'coins','icon':'🪙','name':'200 Münzen','value':'200'},
        {'type':'item', 'icon':'🗡️','name':'Hüter-Form','value':'s1_body_guardian'},
        {'type':'item', 'icon':'💚','name':'Streak-Heiler ×2','value':'streak_healer'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×3','value':'xp_boost_24h'},
        {'type':'item', 'icon':'🌊','name':'Tiefsee-Aura','value':'s1_aura_deep'},
        {'type':'title','icon':'👑','name':'Held des Aufstiegs','value':'Held des Aufstiegs'},
        {'type':'coins','icon':'🪙','name':'250 Münzen','value':'250'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×3','value':'xp_boost_24h'},
        {'type':'item', 'icon':'🔮','name':'Jenseitiger Zyklus','value':'s1_aura_beyond'},
        {'type':'title','icon':'🏆','name':'Vollendeter Aufstieg','value':'Vollendeter Aufstieg'},
        {'type':'coins','icon':'🪙','name':'300 Münzen','value':'300'},
        {'type':'item', 'icon':'🛡️','name':'Streak-Schild ×3','value':'streak_shield'},
        {'type':'item', 'icon':'💚','name':'Streak-Heiler ×2','value':'streak_healer'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×4','value':'xp_boost_24h'},
        {'type':'item', 'icon':'🌟','name':'Legendäre Krönung','value':'s1_aura_legend'},
        {'type':'title','icon':'⭐','name':'Unsterblicher Aufstieg','value':'Unsterblicher Aufstieg'},
        {'type':'coins','icon':'🪙','name':'400 Münzen','value':'400'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×5','value':'xp_boost_24h'},
        {'type':'item', 'icon':'💚','name':'Streak-Heiler ×3','value':'streak_healer'},
        {'type':'item', 'icon':'✨','name':'Absolutes Bewusstsein','value':'s1_aura_absolute'},
        {'type':'coins','icon':'🪙','name':'500 Münzen','value':'500'},
        {'type':'item', 'icon':'🛡️','name':'Streak-Schild ×3','value':'streak_shield'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×5','value':'xp_boost_24h'},
        {'type':'coins','icon':'🪙','name':'750 Münzen','value':'750'},
        {'type':'item', 'icon':'🌟','name':'Göttliche Aufstiegs-Form','value':'s1_body_divine'},
    ]

    S2 = [
        {'type':'title','icon':'🌑','name':'Schattenläufer','value':'Schattenläufer'},
        {'type':'coins','icon':'🪙','name':'30 Münzen','value':'30'},
        {'type':'item', 'icon':'🕳️','name':'Leeren-Aura','value':'s2_aura_void'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost','value':'xp_boost_24h'},
        {'type':'title','icon':'🌙','name':'Dunkler Pfadfinder','value':'Dunkler Pfadfinder'},
        {'type':'coins','icon':'🪙','name':'50 Münzen','value':'50'},
        {'type':'item', 'icon':'🌙','name':'Nachtschwärmer-Aura','value':'s2_aura_night'},
        {'type':'item', 'icon':'🛡️','name':'Streak-Schild','value':'streak_shield'},
        {'type':'coins','icon':'🪙','name':'70 Münzen','value':'70'},
        {'type':'item', 'icon':'💚','name':'Streak-Heiler','value':'streak_healer'},
        {'type':'title','icon':'🌑','name':'Herr der Stille','value':'Herr der Stille'},
        {'type':'coins','icon':'🪙','name':'90 Münzen','value':'90'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×2','value':'xp_boost_24h'},
        {'type':'item', 'icon':'👻','name':'Geisterform','value':'s2_body_ghost'},
        {'type':'title','icon':'🕶️','name':'Schatten-Jäger','value':'Schatten-Jäger'},
        {'type':'coins','icon':'🪙','name':'110 Münzen','value':'110'},
        {'type':'item', 'icon':'🌑','name':'Schattenriss-Aura','value':'s2_aura_shadow'},
        {'type':'item', 'icon':'💚','name':'Streak-Heiler ×2','value':'streak_healer'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×2','value':'xp_boost_24h'},
        {'type':'item', 'icon':'🛡️','name':'Streak-Schild ×2','value':'streak_shield'},
        {'type':'title','icon':'🌑','name':'Geist der Dunkelheit','value':'Geist der Dunkelheit'},
        {'type':'coins','icon':'🪙','name':'160 Münzen','value':'160'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×3','value':'xp_boost_24h'},
        {'type':'item', 'icon':'💚','name':'Streak-Heiler ×2','value':'streak_healer'},
        {'type':'title','icon':'👁️','name':'Der Namenlose','value':'Der Namenlose'},
        {'type':'coins','icon':'🪙','name':'220 Münzen','value':'220'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×3','value':'xp_boost_24h'},
        {'type':'item', 'icon':'🛡️','name':'Streak-Schild ×3','value':'streak_shield'},
        {'type':'item', 'icon':'💚','name':'Streak-Heiler ×3','value':'streak_healer'},
        {'type':'item', 'icon':'🌑','name':'Schatten-Inkarnation','value':'s2_body_shade'},
        {'type':'title','icon':'👑','name':'Meister des Schattens','value':'Meister des Schattens'},
        {'type':'coins','icon':'🪙','name':'280 Münzen','value':'280'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×3','value':'xp_boost_24h'},
        {'type':'item', 'icon':'💚','name':'Streak-Heiler ×3','value':'streak_healer'},
        {'type':'title','icon':'🌑','name':'Fürst des Nichts','value':'Fürst des Nichts'},
        {'type':'coins','icon':'🪙','name':'350 Münzen','value':'350'},
        {'type':'item', 'icon':'🛡️','name':'Streak-Schild ×3','value':'streak_shield'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×4','value':'xp_boost_24h'},
        {'type':'item', 'icon':'💚','name':'Streak-Heiler ×3','value':'streak_healer'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×4','value':'xp_boost_24h'},
        {'type':'title','icon':'☠️','name':'Der Ewige Schatten','value':'Der Ewige Schatten'},
        {'type':'coins','icon':'🪙','name':'450 Münzen','value':'450'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×5','value':'xp_boost_24h'},
        {'type':'item', 'icon':'💚','name':'Streak-Heiler ×4','value':'streak_healer'},
        {'type':'item', 'icon':'🛡️','name':'Streak-Schild ×4','value':'streak_shield'},
        {'type':'coins','icon':'🪙','name':'600 Münzen','value':'600'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×5','value':'xp_boost_24h'},
        {'type':'item', 'icon':'💚','name':'Streak-Heiler ×5','value':'streak_healer'},
        {'type':'coins','icon':'🪙','name':'800 Münzen','value':'800'},
        {'type':'item', 'icon':'🌑','name':'Göttlicher Schatten','value':'s2_body_shade'},
    ]

    S3 = [
        {'type':'title','icon':'🔥','name':'Feuerwacht','value':'Feuerwacht'},
        {'type':'coins','icon':'🪙','name':'30 Münzen','value':'30'},
        {'type':'item', 'icon':'🔥','name':'Glutkern-Aura','value':'s3_aura_ember'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost','value':'xp_boost_24h'},
        {'type':'title','icon':'🌋','name':'Flammengeboren','value':'Flammengeboren'},
        {'type':'coins','icon':'🪙','name':'50 Münzen','value':'50'},
        {'type':'item', 'icon':'🛡️','name':'Streak-Schild','value':'streak_shield'},
        {'type':'item', 'icon':'💚','name':'Streak-Heiler','value':'streak_healer'},
        {'type':'coins','icon':'🪙','name':'70 Münzen','value':'70'},
        {'type':'item', 'icon':'🔥','name':'Flammenreiter-Form','value':'s3_body_fire'},
        {'type':'title','icon':'🔥','name':'Hüter des Feuers','value':'Hüter des Feuers'},
        {'type':'coins','icon':'🪙','name':'90 Münzen','value':'90'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×2','value':'xp_boost_24h'},
        {'type':'item', 'icon':'💚','name':'Streak-Heiler ×2','value':'streak_healer'},
        {'type':'title','icon':'🌋','name':'Aschereiter','value':'Aschereiter'},
        {'type':'coins','icon':'🪙','name':'120 Münzen','value':'120'},
        {'type':'item', 'icon':'🌋','name':'Höllenfeuer-Aura','value':'s3_aura_hellfire'},
        {'type':'item', 'icon':'🛡️','name':'Streak-Schild ×2','value':'streak_shield'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×2','value':'xp_boost_24h'},
        {'type':'item', 'icon':'💚','name':'Streak-Heiler ×2','value':'streak_healer'},
        {'type':'title','icon':'😈','name':'Dämonenfürst','value':'Dämonenfürst'},
        {'type':'coins','icon':'🪙','name':'180 Münzen','value':'180'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×3','value':'xp_boost_24h'},
        {'type':'item', 'icon':'🛡️','name':'Streak-Schild ×2','value':'streak_shield'},
        {'type':'title','icon':'🔥','name':'Flammen-Gott','value':'Flammen-Gott'},
        {'type':'coins','icon':'🪙','name':'250 Münzen','value':'250'},
        {'type':'item', 'icon':'💚','name':'Streak-Heiler ×3','value':'streak_healer'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×3','value':'xp_boost_24h'},
        {'type':'item', 'icon':'🛡️','name':'Streak-Schild ×3','value':'streak_shield'},
        {'type':'item', 'icon':'😈','name':'Dämonische Inkarnation','value':'s3_body_demon'},
        {'type':'title','icon':'🌋','name':'Herr des Infernos','value':'Herr des Infernos'},
        {'type':'coins','icon':'🪙','name':'320 Münzen','value':'320'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×4','value':'xp_boost_24h'},
        {'type':'item', 'icon':'💚','name':'Streak-Heiler ×3','value':'streak_healer'},
        {'type':'title','icon':'😈','name':'Verkörperung des Chaos','value':'Verkörperung des Chaos'},
        {'type':'coins','icon':'🪙','name':'400 Münzen','value':'400'},
        {'type':'item', 'icon':'🛡️','name':'Streak-Schild ×4','value':'streak_shield'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×4','value':'xp_boost_24h'},
        {'type':'item', 'icon':'💚','name':'Streak-Heiler ×4','value':'streak_healer'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×5','value':'xp_boost_24h'},
        {'type':'title','icon':'☄️','name':'Der Unvergängliche','value':'Der Unvergängliche'},
        {'type':'coins','icon':'🪙','name':'500 Münzen','value':'500'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×5','value':'xp_boost_24h'},
        {'type':'item', 'icon':'💚','name':'Streak-Heiler ×5','value':'streak_healer'},
        {'type':'item', 'icon':'🛡️','name':'Streak-Schild ×5','value':'streak_shield'},
        {'type':'coins','icon':'🪙','name':'700 Münzen','value':'700'},
        {'type':'item', 'icon':'⚡','name':'XP-Boost ×6','value':'xp_boost_24h'},
        {'type':'item', 'icon':'💚','name':'Streak-Heiler ×5','value':'streak_healer'},
        {'type':'coins','icon':'🪙','name':'1000 Münzen','value':'1000'},
        {'type':'item', 'icon':'😈','name':'Göttliche Dämonischen Form','value':'s3_body_demon'},
    ]

    return [
        {'id':1,'name':'Der Aufstieg',   'icon':'⬆️','color':'#00d4ff','tiers':_tiers(S1)},
        {'id':2,'name':'Die Dunkelheit', 'icon':'🌑','color':'#9b59b6','tiers':_tiers(S2)},
        {'id':3,'name':'Das Inferno',    'icon':'🔥','color':'#e74c3c','tiers':_tiers(S3)},
    ]

SEASON_PASS_DATA = _build_season_pass_data()

SHOP_SEED = [
    # (item_key, name, description, category, icon, cost, rarity, effect_type, effect_value, unlock_level, stackable)
    ('blue_aura',      'Blaue Aura',         'Ruhige Energie um deinen Charakter',       'cosmetic_aura',  '🔵',  20,   'common',    'aura','blue',     1,  0),
    ('green_aura',     'Grüne Aura',          'Frische Lebensenergie',                    'cosmetic_aura',  '🟢',  35,   'common',    'aura','green',    3,  0),
    ('title_diligent', 'Der Fleißige',        'Dein erster Titel',                        'title',          '📜',  15,   'common',    'title','Der Fleißige', 1, 0),
    ('gold_crown',     'Goldene Krone',       'Ein Zeichen der Stärke',                   'cosmetic_body',  '👑',  60,   'rare',      'body','crown',    5,  0),
    ('purple_aura',    'Purpur-Aura',         'Mystische violette Macht',                 'cosmetic_aura',  '🟣',  80,   'rare',      'aura','purple',   8,  0),
    ('title_quester',  'Quest-Meister',       'Du meisterst Quest nach Quest',            'title',          '⚔️',  80,   'rare',      'title','Quest-Meister', 15, 0),
    ('xp_boost_24h',   'XP-Boost 24h',       '+50% XP für 24 Stunden',                  'consumable',     '⚡',  55,   'rare',      'xp_boost','1.5',  1,  1),
    ('streak_shield',  'Streak-Schild',       'Schützt deinen Habit-Streak einmal',      'consumable',     '🛡️',  80,   'rare',      'streak_shield','1', 5, 1),
    ('xp_master_1',    'XP-Meister I',       '+10% XP permanent',                        'upgrade',        '🔮',  350,  'rare',      'xp_perm','0.10', 15,  0),
    ('streak_healer',  'Streak-Heiler',       'Repariert einen verlorenen Streak-Tag',    'consumable',     '💚',  160,  'epic',      'streak_heal','1', 10, 1),
    ('dragon_aura',    'Drachen-Aura',        'Die Kraft des Drachen fließt um dich',    'cosmetic_aura',  '🐉',  320,  'epic',      'aura','dragon',   25,  0),
    ('title_focus',    'Fokus-Gott',          'Maximale Konzentration, max. Leistung',    'title',          '🎯',  220,  'epic',      'title','Fokus-Gott', 30, 0),
    ('double_coins',   'Doppelte Münzen 24h', 'Level-ups geben 2× Münzen',               'consumable',     '🪙',  110,  'epic',      'coin_boost_temp','2.0', 10, 1),
    ('xp_master_2',    'XP-Meister II',      '+25% XP permanent (req. XP-Meister I)',    'upgrade',        '💎',  1100, 'epic',      'xp_perm','0.25', 40,  0),
    ('coin_magnet',    'Münzmagnet',          '+30% Münzen bei Level-ups permanent',      'upgrade',        '🧲',  450,  'rare',      'coin_perm','0.30', 25, 0),
    ('rainbow_aura',   'Regenbogen-Aura',     'Das volle Spektrum der Produktivität',     'cosmetic_aura',  '🌈',  550,  'epic',      'aura','rainbow',  50,  0),
    ('title_unstop',   'Der Unaufhaltsame',   'Nichts kann dich stoppen',                 'title',          '👹',  550,  'legendary', 'title','Der Unaufhaltsame', 60, 0),
    ('shadow_cloak',   'Schatten-Mantel',     'Dunkle Macht des Schattens',               'cosmetic_body',  '🕶️',  800,  'legendary', 'body','shadow',   75,  0),
    ('divine_halo',    'Göttliche Aureole',   'Für Produktivitäts-Götter',                'cosmetic_aura',  '✨',  2200, 'legendary', 'aura','divine',  100,  0),
    ('title_legend',   'Legende',             'Du bist eine Produktivitäts-Legende',      'title',          '🏆',  1100, 'legendary', 'title','Legende', 100, 0),
    ('xp_master_3',    'XP-Meister III',     '+50% XP permanent (req. II)',               'upgrade',        '🌟',  3000, 'legendary', 'xp_perm','0.50', 75,  0),
    ('godly_body',     'Göttlicher Körper',   'Die ultimative Form',                       'cosmetic_body',  '🌟',  5000, 'legendary', 'body','godly',   200,  0),
]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni",
          "Juli", "August", "September", "Oktober", "November", "Dezember"]

TYPE_LABELS = {"highlight": "⭐ Highlight", "micro": "⏱️ Micro", "brain": "📝 To-Do"}


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY,
        entry_type TEXT,
        content TEXT,
        tags TEXT,
        priority INTEGER DEFAULT 0,
        estimate_minutes INTEGER DEFAULT 0,
        points INTEGER DEFAULT 0,
        created_at TEXT,
        entry_date TEXT,
        done INTEGER DEFAULT 0,
        completed_at TEXT,
        elapsed_seconds INTEGER DEFAULT 0,
        last_modified TEXT,
        started_at TEXT,
        deadline TEXT
    )
    ''')
    c.execute("PRAGMA table_info(entries)")
    cols = [r[1] for r in c.fetchall()]
    for col, typedef in [('started_at','TEXT'),('deadline','TEXT'),('micro_action','TEXT'),('category_id','INTEGER')]:
        if col not in cols:
            try:
                c.execute(f'ALTER TABLE entries ADD COLUMN {col} {typedef}')
            except Exception:
                pass
    c.execute("PRAGMA table_info(project_tasks)")
    pt_cols = [r[1] for r in c.fetchall()]
    if 'notes' not in pt_cols:
        try:
            c.execute("ALTER TABLE project_tasks ADD COLUMN notes TEXT DEFAULT ''")
        except Exception:
            pass
    if 'highlight_color' not in pt_cols:
        try:
            c.execute("ALTER TABLE project_tasks ADD COLUMN highlight_color TEXT DEFAULT ''")
        except Exception:
            pass
    c.execute('''
    CREATE TABLE IF NOT EXISTS task_categories (
        id   INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        icon TEXT DEFAULT '📌',
        color TEXT DEFAULT '#636e72',
        base_xp INTEGER DEFAULT 100,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    # Seed default categories if table is empty
    if not c.execute("SELECT COUNT(*) FROM task_categories").fetchone()[0]:
        defaults = [
            ('🧠 Brain Work',    '🧠','#9b59b6',120,0),
            ('⚡ Quick Win',     '⚡','#27ae60', 50,1),
            ('💪 Deep Focus',    '💪','#e74c3c',200,2),
            ('🎯 Strategisch',   '🎯','#ffd700',150,3),
            ('📞 Kommunikation', '📞','#3498db', 80,4),
        ]
        for (nm,ic,cl,xp,so) in defaults:
            c.execute("INSERT INTO task_categories (name,icon,color,base_xp,sort_order) VALUES (?,?,?,?,?)",
                      (nm,ic,cl,xp,so))
    c.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY,
        name TEXT,
        description TEXT,
        deadline TEXT,
        color TEXT DEFAULT '#60a5fa',
        active INTEGER DEFAULT 1,
        created_at TEXT,
        daily_minutes INTEGER DEFAULT 60
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS project_tasks (
        id INTEGER PRIMARY KEY,
        project_id INTEGER,
        content TEXT,
        estimate_minutes INTEGER DEFAULT 30,
        priority INTEGER DEFAULT 5,
        done INTEGER DEFAULT 0,
        completed_at TEXT,
        scheduled_date TEXT,
        order_index INTEGER DEFAULT 0,
        created_at TEXT,
        notes TEXT DEFAULT '',
        highlight_color TEXT DEFAULT ''
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS recurring_tasks (
        id INTEGER PRIMARY KEY,
        entry_type TEXT DEFAULT 'brain',
        content TEXT,
        tags TEXT,
        estimate_minutes INTEGER DEFAULT 0,
        recurrence TEXT DEFAULT '0,1,2,3,4,5,6',
        time_of_day TEXT DEFAULT 'anytime',
        active INTEGER DEFAULT 1,
        created_at TEXT,
        last_generated TEXT
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY,
        review_type TEXT,
        content TEXT,
        review_date TEXT,
        created_at TEXT
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS ki_insights (
        id INTEGER PRIMARY KEY,
        category TEXT,
        insight TEXT,
        created_at TEXT
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS habits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT DEFAULT 'general',
        icon TEXT DEFAULT '⭐',
        color TEXT DEFAULT '#00d4ff',
        sort_order INTEGER DEFAULT 0,
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS habit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        habit_id INTEGER REFERENCES habits(id) ON DELETE CASCADE,
        log_date TEXT NOT NULL,
        energy_level INTEGER NOT NULL DEFAULT 100,
        completion_pct INTEGER NOT NULL DEFAULT 0,
        notes TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(habit_id, log_date)
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS character_data (
        id INTEGER PRIMARY KEY,
        name TEXT DEFAULT 'Hero',
        class_id TEXT DEFAULT '',
        total_xp INTEGER DEFAULT 0,
        coins INTEGER DEFAULT 0,
        equipped_title TEXT DEFAULT '',
        equipped_aura TEXT DEFAULT '',
        equipped_body TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS shop_items (
        id INTEGER PRIMARY KEY,
        item_key TEXT UNIQUE,
        name TEXT,
        description TEXT,
        category TEXT,
        icon TEXT,
        cost_coins INTEGER DEFAULT 50,
        rarity TEXT DEFAULT 'common',
        effect_type TEXT DEFAULT '',
        effect_value TEXT DEFAULT '',
        unlock_level INTEGER DEFAULT 1,
        stackable INTEGER DEFAULT 0
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS player_inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_key TEXT,
        purchased_at TEXT DEFAULT CURRENT_TIMESTAMP,
        equipped INTEGER DEFAULT 0,
        uses_remaining INTEGER DEFAULT -1
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS level_ups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level_reached INTEGER,
        coins_earned INTEGER,
        achieved_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS player_season (
        id INTEGER PRIMARY KEY,
        season_id INTEGER DEFAULT 1,
        season_xp INTEGER DEFAULT 0
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS season_claimed (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        season_id INTEGER,
        tier_number INTEGER,
        claimed_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(season_id, tier_number)
    )
    ''')
    # Seed shop items
    for (ik,nm,desc,cat,icon,cost,rar,eft,efv,unlvl,stack) in SHOP_SEED:
        c.execute("""
            INSERT OR IGNORE INTO shop_items
            (item_key,name,description,category,icon,cost_coins,rarity,effect_type,effect_value,unlock_level,stackable)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (ik,nm,desc,cat,icon,cost,rar,eft,efv,unlvl,stack))
    # Seed season exclusive items
    for (ik,nm,desc,cat,icon,cost,rar,eft,efv,unlvl,stack) in SEASON_EXCLUSIVE_ITEMS:
        c.execute("""
            INSERT OR IGNORE INTO shop_items
            (item_key,name,description,category,icon,cost_coins,rarity,effect_type,effect_value,unlock_level,stackable)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (ik,nm,desc,cat,icon,cost,rar,eft,efv,unlvl,stack))
    # Ensure player_season row exists
    c.execute("INSERT OR IGNORE INTO player_season (id,season_id,season_xp) VALUES (1,1,0)")
    c.execute('''
    CREATE TABLE IF NOT EXISTS task_steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_id INTEGER NOT NULL,
        step_number INTEGER NOT NULL,
        content TEXT NOT NULL,
        done INTEGER DEFAULT 0,
        completed_at TEXT,
        UNIQUE(entry_id, step_number)
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS task_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_id INTEGER UNIQUE NOT NULL,
        summary TEXT,
        time_estimate INTEGER DEFAULT 0,
        context_note TEXT,
        analyzed_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    # ─── Calisthenics Trainingssystem ──────────────────────────
    c.execute('''
    CREATE TABLE IF NOT EXISTS cal_progress (
        track TEXT PRIMARY KEY,
        current_level INTEGER DEFAULT 0,
        consecutive_clean INTEGER DEFAULT 0,
        bonus_reps INTEGER DEFAULT 0,
        best_reps INTEGER DEFAULT 0,
        updated_at TEXT
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS cal_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_date TEXT NOT NULL,
        track TEXT NOT NULL,
        exercise_name TEXT,
        level_idx INTEGER,
        sets_completed INTEGER,
        target_sets INTEGER,
        best_reps INTEGER,
        target_reps INTEGER,
        is_hold INTEGER DEFAULT 0,
        clean INTEGER DEFAULT 0,
        notes TEXT,
        created_at TEXT
    )
    ''')
    # ─── Schlafrythmus & Routinen ───────────────────────────────
    c.execute('''
    CREATE TABLE IF NOT EXISTS routine_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_date TEXT NOT NULL,
        routine TEXT NOT NULL,
        task_key TEXT NOT NULL,
        done INTEGER DEFAULT 0,
        created_at TEXT,
        UNIQUE(log_date, routine, task_key)
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS sleep_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_date TEXT UNIQUE NOT NULL,
        quality_pct INTEGER,
        bedtime TEXT,
        wake_time TEXT,
        notes TEXT,
        created_at TEXT
    )
    ''')
    # ─── Haushalt ─────────────────────────────────────────────────
    c.execute('''
    CREATE TABLE IF NOT EXISTS household_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_key TEXT NOT NULL,
        log_date TEXT NOT NULL,
        created_at TEXT,
        UNIQUE(task_key, log_date)
    )
    ''')
    # ─── Spontane Gedanken ───────────────────────────────────────
    c.execute('''
    CREATE TABLE IF NOT EXISTS spontaneous_thoughts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        created_at TEXT,
        sorted INTEGER DEFAULT 0,
        sorted_at TEXT,
        resolution TEXT,
        entry_id INTEGER
    )
    ''')
    conn.commit()
    conn.close()


def get_setting(key, default=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT value FROM settings WHERE key=?', (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default


def set_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)', (key, str(value)))
    conn.commit()
    conn.close()


def add_entry(entry_type, content, tags=None, priority=0, estimate=0, points=0,
              entry_date=None, deadline=None):
    now = datetime.utcnow().isoformat()
    entry_date = entry_date or date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO entries
                 (entry_type, content, tags, priority, estimate_minutes, points,
                  created_at, entry_date, last_modified, deadline)
                 VALUES (?,?,?,?,?,?,?,?,?,?)''',
              (entry_type, content, tags or "", priority, estimate, points,
               now, entry_date, now, deadline or ""))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    _schedule_backup()
    return new_id


def _schedule_backup():
    """Set a flag so the next rerun triggers a backup. Non-blocking."""
    try:
        import streamlit as _st
        _st.session_state['_backup_pending'] = True
    except Exception:
        pass


def get_categories():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id,name,icon,color,base_xp,sort_order FROM task_categories ORDER BY sort_order,id"
    ).fetchall()
    conn.close()
    keys = ['id','name','icon','color','base_xp','sort_order']
    return [dict(zip(keys,r)) for r in rows]


def get_category(cat_id):
    if not cat_id:
        return None
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT id,name,icon,color,base_xp,sort_order FROM task_categories WHERE id=?", (cat_id,)
    ).fetchone()
    conn.close()
    if row:
        return dict(zip(['id','name','icon','color','base_xp','sort_order'], row))
    return None


def set_entry_category(entry_id, category_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE entries SET category_id=? WHERE id=?", (category_id, entry_id))
    conn.commit()
    conn.close()


# ── Task Steps ──────────────────────────────────────────────────

def get_task_steps(entry_id):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, step_number, content, done, completed_at FROM task_steps "
        "WHERE entry_id=? ORDER BY step_number", (entry_id,)
    ).fetchall()
    conn.close()
    return [{'id': r[0], 'step_number': r[1], 'content': r[2], 'done': bool(r[3]), 'completed_at': r[4]} for r in rows]


def save_task_steps(entry_id, steps):
    """Replace all steps for an entry. steps = list of strings."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM task_steps WHERE entry_id=?", (entry_id,))
    for i, s in enumerate(steps, 1):
        conn.execute("INSERT OR REPLACE INTO task_steps (entry_id, step_number, content) VALUES (?,?,?)",
                     (entry_id, i, s.strip()))
    conn.commit()
    conn.close()


def toggle_step(step_id, done):
    conn = sqlite3.connect(DB_PATH)
    ts = datetime.utcnow().isoformat() if done else None
    conn.execute("UPDATE task_steps SET done=?, completed_at=? WHERE id=?", (int(done), ts, step_id))
    conn.commit()
    conn.close()


def get_task_analysis(entry_id):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT summary, time_estimate, context_note, analyzed_at FROM task_analysis WHERE entry_id=?",
        (entry_id,)
    ).fetchone()
    conn.close()
    if row:
        return {'summary': row[0], 'time_estimate': row[1], 'context_note': row[2], 'analyzed_at': row[3]}
    return None


def save_task_analysis(entry_id, summary, time_estimate, context_note):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO task_analysis (entry_id, summary, time_estimate, context_note, analyzed_at) "
        "VALUES (?,?,?,?,?)",
        (entry_id, summary, time_estimate, context_note, datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


def get_today_entries():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT id, entry_type, content, tags, priority, estimate_minutes, points,
                        created_at, entry_date, done, completed_at, elapsed_seconds, started_at,
                        deadline, micro_action, category_id
                 FROM entries WHERE entry_date=? ORDER BY id DESC''', (date.today().isoformat(),))
    rows = c.fetchall()
    conn.close()
    return rows


def get_all_entries():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT id, entry_type, content, tags, priority, estimate_minutes, points,
                        created_at, entry_date, done, completed_at, elapsed_seconds, started_at,
                        deadline, micro_action, category_id
                 FROM entries ORDER BY entry_date DESC, id DESC''')
    rows = c.fetchall()
    conn.close()
    return rows


def toggle_done(entry_id, new, elapsed_seconds=0, points=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    if new:
        if points is None:
            points = POINTS_PER_TASK
        c.execute('UPDATE entries SET done=1, completed_at=?, elapsed_seconds=?, points=?, last_modified=?, started_at=NULL WHERE id=?',
                  (now, elapsed_seconds, points, now, entry_id))
        conn.commit()
        conn.close()
        _schedule_backup()
        # Award XP based on task type
        row_e = sqlite3.connect(DB_PATH).execute(
            "SELECT entry_type, estimate_minutes, category_id FROM entries WHERE id=?", (entry_id,)
        ).fetchone()
        if row_e:
            etype, est_min, cat_id = row_e
            cat = get_category(cat_id) if cat_id else None
            xp_base = cat['base_xp'] if cat else {'highlight': 200, 'brain': 100, 'micro': 50}.get(etype, 100)
            est_secs = (est_min or 0) * 60
            is_fast = est_secs > 0 and 0 < elapsed_seconds < est_secs
            if is_fast:
                xp_base += 30
            award_xp(xp_base, entry_type=etype, speed_bonus=is_fast)
    else:
        c.execute('UPDATE entries SET done=0, completed_at=NULL, elapsed_seconds=0, points=0, last_modified=?, started_at=NULL WHERE id=?',
                  (now, entry_id))
        conn.commit()
        conn.close()


def total_points():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT SUM(points) FROM entries')
    s = c.fetchone()[0] or 0
    conn.close()
    return s


def get_level_and_progress():
    try:
        level_step = int(get_setting('level_step') or LEVEL_STEP)
    except Exception:
        level_step = LEVEL_STEP
    pts = total_points()
    level = pts // level_step
    progress = pts % level_step
    return level, progress, level_step


def start_task(entry_id):
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE entries SET started_at=?, last_modified=? WHERE id=?', (now, now, entry_id))
    conn.commit()
    conn.close()


def compute_points(elapsed_seconds, estimate_minutes):
    elapsed_minutes = int(round(elapsed_seconds / 60)) if elapsed_seconds else 0
    try:
        base = int(get_setting('points_per_task') or POINTS_PER_TASK)
    except Exception:
        base = POINTS_PER_TASK
    bonus = 0
    if estimate_minutes and estimate_minutes > 0:
        saved = max(0, estimate_minutes - elapsed_minutes)
        bonus = saved * 2
    if elapsed_minutes <= 5:
        bonus += 1
    return base + bonus


def get_urgency(deadline_str):
    """Returns (level, days_left, label, css_class) for a deadline string."""
    if not deadline_str:
        return "none", 9999, "", "urg-none"
    try:
        dl = date.fromisoformat(deadline_str)
        days_left = (dl - date.today()).days
        if days_left < 0:
            return "overdue", days_left, f"🔴 {abs(days_left)}T überfällig!", "urg-overdue"
        elif days_left == 0:
            return "today", 0, "🟠 Heute fällig!", "urg-today"
        elif days_left == 1:
            return "tomorrow", 1, "🟡 Morgen fällig", "urg-tomorrow"
        elif days_left <= 3:
            return "soon", days_left, f"🟢 Noch {days_left} Tage", "urg-soon"
        else:
            return "later", days_left, f"📅 {dl.strftime('%d.%m.%Y')}", "urg-later"
    except Exception:
        return "none", 9999, "", "urg-none"


# ========== ANALYTICS & PREDICTION ==========

def get_average_duration_by_type(entry_type):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT AVG(elapsed_seconds) FROM entries WHERE entry_type=? AND done=1 AND elapsed_seconds>0", (entry_type,))
    result = c.fetchone()[0]
    conn.close()
    return int(result / 60) if result else None


def get_average_duration_by_tags(tags_str):
    if not tags_str:
        return None
    tags_list = [t.strip() for t in tags_str.split(',')]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    durations = []
    for tag in tags_list:
        c.execute("SELECT AVG(elapsed_seconds) FROM entries WHERE tags LIKE ? AND done=1 AND elapsed_seconds>0", (f'%{tag}%',))
        result = c.fetchone()[0]
        if result:
            durations.append(int(result / 60))
    conn.close()
    return int(np.mean(durations)) if durations else None


def predict_duration(entry_type, tags=None, estimate_minutes=None):
    if estimate_minutes and estimate_minutes > 0:
        return estimate_minutes
    tag_avg = get_average_duration_by_tags(tags) if tags else None
    type_avg = get_average_duration_by_type(entry_type)
    predictions = [p for p in [tag_avg, type_avg] if p is not None]
    if predictions:
        return int(np.mean(predictions))
    return {"brain": 5, "highlight": 25, "micro": 2}.get(entry_type, 10)


def get_analytics_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM entries WHERE done=1")
    completed_tasks = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM entries")
    total_tasks = c.fetchone()[0]
    c.execute("SELECT SUM(elapsed_seconds) FROM entries WHERE done=1")
    total_time = c.fetchone()[0] or 0
    c.execute("SELECT entry_type, COUNT(*), AVG(elapsed_seconds), SUM(elapsed_seconds) FROM entries WHERE done=1 GROUP BY entry_type")
    type_stats = c.fetchall()
    c.execute("SELECT tags, COUNT(*), AVG(elapsed_seconds) FROM entries WHERE done=1 AND tags IS NOT NULL AND tags!='' GROUP BY tags")
    tag_stats = c.fetchall()
    c.execute("""
        SELECT DATE(completed_at) as day, COUNT(*), SUM(elapsed_seconds)
        FROM entries WHERE done=1 AND completed_at IS NOT NULL
        AND completed_at > datetime('now', '-30 days')
        GROUP BY DATE(completed_at) ORDER BY day
    """)
    daily_trend = c.fetchall()
    conn.close()
    return {
        "completed": completed_tasks, "total": total_tasks,
        "total_minutes": int(total_time / 60),
        "type_stats": type_stats, "tag_stats": tag_stats, "daily_trend": daily_trend
    }


# ─── RPG / XP System ────────────────────────────────────────────

def xp_for_next_level(level):
    return 150 + (level - 1) * 50


def compute_level(total_xp):
    """Returns (level, xp_in_current_level, xp_needed_for_next)."""
    level, remaining = 1, max(0, total_xp)
    while True:
        needed = xp_for_next_level(level)
        if remaining >= needed:
            remaining -= needed
            level += 1
        else:
            return level, remaining, needed


def get_character():
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT id,name,class_id,total_xp,coins,equipped_title,equipped_aura,equipped_body FROM character_data LIMIT 1"
    ).fetchone()
    conn.close()
    if not row:
        return None
    return dict(zip(["id","name","class_id","total_xp","coins","equipped_title","equipped_aura","equipped_body"], row))


def save_character(name, class_id):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT id FROM character_data").fetchone()
    if row:
        conn.execute("UPDATE character_data SET name=?,class_id=? WHERE id=1", (name, class_id))
    else:
        conn.execute("INSERT INTO character_data (id,name,class_id,total_xp,coins) VALUES (1,?,?,0,0)",
                      (name, class_id))
    conn.commit()
    conn.close()


def get_inv_by_effect(effect_type):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT pi.item_key, si.effect_value FROM player_inventory pi
        JOIN shop_items si ON si.item_key=pi.item_key
        WHERE si.effect_type=? AND (pi.equipped=1 OR si.category='upgrade')
    """, (effect_type,)).fetchall()
    conn.close()
    return [{'item_key': r[0], 'effect_value': r[1]} for r in rows]


def award_xp(base_xp, entry_type=None, speed_bonus=False):
    """Awards XP with class bonus + boosts. Returns (new_level, leveled_up, coins_earned, final_xp)."""
    char = get_character()
    if not char:
        return 1, False, 0, 0

    mult = 1.0

    # Class bonus
    if char.get('class_id') and entry_type:
        ci = CLASS_INFO.get(char['class_id'], {})
        bt = ci.get('bonus_type', '')
        if bt == entry_type or (bt == 'speed' and speed_bonus):
            mult += ci.get('bonus_mult', 0)

    # Permanent XP upgrades
    for upg in get_inv_by_effect('xp_perm'):
        try:
            mult += float(upg['effect_value'])
        except Exception:
            pass

    # Temporary XP boost (consumable)
    expiry_str = get_setting('xp_boost_expiry', '')
    if expiry_str:
        try:
            if datetime.fromisoformat(expiry_str) > datetime.utcnow():
                mult *= float(get_setting('xp_boost_multiplier', '1.5'))
        except Exception:
            pass

    final_xp = max(1, round(base_xp * mult))

    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT total_xp, coins FROM character_data WHERE id=1").fetchone()
    if not row:
        conn.execute("INSERT INTO character_data (id,name,total_xp,coins) VALUES (1,'Hero',?,0)", (final_xp,))
        conn.commit()
        conn.close()
        return 1, False, 0, final_xp

    old_xp = row[0]
    old_level = compute_level(old_xp)[0]
    new_xp = old_xp + final_xp
    new_level = compute_level(new_xp)[0]
    leveled_up = new_level > old_level
    coins_earned = 0

    if leveled_up:
        # Coin magnet perk
        coin_bonus = sum(float(u['effect_value']) for u in get_inv_by_effect('coin_perm'))
        # Temp coin boost
        cb_expiry = get_setting('coin_boost_expiry', '')
        cb_mult = 1.0
        if cb_expiry:
            try:
                if datetime.fromisoformat(cb_expiry) > datetime.utcnow():
                    cb_mult = float(get_setting('coin_boost_mult', '2.0'))
            except Exception:
                pass
        for lv in range(old_level, new_level):
            base_coins = 10 + lv * 5
            coins_earned += round(base_coins * (1.0 + coin_bonus) * cb_mult)
        conn.execute("UPDATE character_data SET total_xp=?,coins=coins+? WHERE id=1", (new_xp, coins_earned))
        conn.execute("INSERT INTO level_ups (level_reached,coins_earned) VALUES (?,?)", (new_level, coins_earned))
    else:
        conn.execute("UPDATE character_data SET total_xp=? WHERE id=1", (new_xp,))

    conn.commit()
    conn.close()

    if leveled_up:
        if 'levelup_queue' not in st.session_state:
            st.session_state.levelup_queue = []
        st.session_state.levelup_queue.append({'level': new_level, 'coins': coins_earned, 'xp': final_xp})

    # Award season XP in parallel
    _award_season_xp(final_xp)

    return new_level, leveled_up, coins_earned, final_xp


def _award_season_xp(amount):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR IGNORE INTO player_season (id,season_id,season_xp) VALUES (1,1,0)")
    conn.execute("UPDATE player_season SET season_xp=season_xp+? WHERE id=1", (amount,))
    conn.commit()
    conn.close()


def get_player_season():
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT season_id,season_xp FROM player_season WHERE id=1").fetchone()
    conn.close()
    if row:
        return {'season_id': row[0], 'season_xp': row[1]}
    return {'season_id': 1, 'season_xp': 0}


def get_season_claimed(season_id):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT tier_number FROM season_claimed WHERE season_id=?", (season_id,)).fetchall()
    conn.close()
    return {r[0] for r in rows}


def claim_season_reward(season_id, tier_number):
    season = next((s for s in SEASON_PASS_DATA if s['id'] == season_id), None)
    if not season:
        return False, "Season nicht gefunden"
    tier = next((t for t in season['tiers'] if t['tier'] == tier_number), None)
    if not tier:
        return False, "Tier nicht gefunden"

    sp = get_player_season()
    if sp['season_xp'] < tier['xp']:
        return False, "Noch nicht genug Season XP"

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("INSERT INTO season_claimed (season_id,tier_number) VALUES (?,?)", (season_id, tier_number))
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Bereits eingelöst"
    conn.commit()
    conn.close()

    rtype = tier['type']
    rval = tier['value']

    if rtype == 'coins':
        amount = int(rval)
        conn2 = sqlite3.connect(DB_PATH)
        conn2.execute("UPDATE character_data SET coins=coins+? WHERE id=1", (amount,))
        conn2.commit()
        conn2.close()
        return True, f"💰 +{amount} Münzen erhalten!"

    elif rtype == 'title':
        conn2 = sqlite3.connect(DB_PATH)
        conn2.execute("UPDATE character_data SET equipped_title=? WHERE id=1", (rval,))
        conn2.commit()
        conn2.close()
        return True, f"🏅 Titel '{rval}' freigeschaltet und ausgerüstet!"

    elif rtype == 'item':
        conn2 = sqlite3.connect(DB_PATH)
        # Handle stackable consumables (add multiple uses)
        item_row = conn2.execute("SELECT stackable,effect_type FROM shop_items WHERE item_key=?", (rval,)).fetchone()
        if item_row:
            existing = conn2.execute(
                "SELECT id,uses_remaining FROM player_inventory WHERE item_key=? AND uses_remaining IS NOT NULL AND uses_remaining > 0",
                (rval,)
            ).fetchone()
            if existing:
                conn2.execute("UPDATE player_inventory SET uses_remaining=uses_remaining+1 WHERE id=?", (existing[0],))
            else:
                conn2.execute(
                    "INSERT INTO player_inventory (item_key,purchased_at,equipped,uses_remaining) VALUES (?,?,0,1)",
                    (rval, datetime.utcnow().isoformat())
                )
        conn2.commit()
        conn2.close()
        return True, f"🎁 '{tier['name']}' erhalten!"

    return True, "Belohnung eingelöst!"


def advance_season_if_complete():
    sp = get_player_season()
    season = next((s for s in SEASON_PASS_DATA if s['id'] == sp['season_id']), None)
    if not season:
        return
    claimed = get_season_claimed(sp['season_id'])
    if len(claimed) >= len(season['tiers']):
        next_sid = sp['season_id'] + 1
        if any(s['id'] == next_sid for s in SEASON_PASS_DATA):
            conn = sqlite3.connect(DB_PATH)
            conn.execute("UPDATE player_season SET season_id=?,season_xp=0 WHERE id=1", (next_sid,))
            conn.commit()
            conn.close()
            return next_sid
    return None


def get_all_shop_items():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT item_key,name,description,category,icon,cost_coins,rarity,effect_type,effect_value,unlock_level,stackable FROM shop_items ORDER BY cost_coins"
    ).fetchall()
    conn.close()
    keys = ["item_key","name","description","category","icon","cost_coins","rarity","effect_type","effect_value","unlock_level","stackable"]
    # Filter out season-exclusive items from the regular shop
    return [dict(zip(keys, r)) for r in rows if r[0] not in SEASON_EXCLUSIVE_KEYS]


def get_inventory():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT pi.id, pi.item_key, pi.equipped, pi.uses_remaining, pi.purchased_at,
               si.name, si.icon, si.rarity, si.effect_type, si.effect_value, si.category, si.description
        FROM player_inventory pi JOIN shop_items si ON si.item_key=pi.item_key
        ORDER BY pi.purchased_at DESC
    """).fetchall()
    conn.close()
    keys = ["id","item_key","equipped","uses_remaining","purchased_at","name","icon","rarity","effect_type","effect_value","category","description"]
    return [dict(zip(keys, r)) for r in rows]


def buy_item(item_key):
    conn = sqlite3.connect(DB_PATH)
    item = conn.execute(
        "SELECT cost_coins,stackable,name,category,effect_type FROM shop_items WHERE item_key=?", (item_key,)
    ).fetchone()
    if not item:
        conn.close()
        return False, "Item nicht gefunden"
    cost, stackable, iname, cat, eff_type = item
    char = conn.execute("SELECT coins FROM character_data WHERE id=1").fetchone()
    if not char:
        conn.close()
        return False, "Erstelle zuerst deinen Charakter!"
    if char[0] < cost:
        conn.close()
        return False, f"Zu wenig Münzen! (hast: {char[0]} · braucht: {cost})"
    if not stackable:
        owned = conn.execute("SELECT id FROM player_inventory WHERE item_key=?", (item_key,)).fetchone()
        if owned:
            conn.close()
            return False, f"Du besitzt '{iname}' bereits"

    conn.execute("UPDATE character_data SET coins=coins-? WHERE id=1", (cost,))
    # consumables get limited uses, upgrades auto-equip
    uses = 3 if cat == 'consumable' else -1
    equipped_val = 1 if cat == 'upgrade' else 0
    conn.execute("INSERT INTO player_inventory (item_key,equipped,uses_remaining) VALUES (?,?,?)",
                  (item_key, equipped_val, uses))
    conn.commit()
    conn.close()
    return True, f"✅ '{iname}' gekauft!"


def equip_item(inv_id, item_key, category):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT equipped FROM player_inventory WHERE id=?", (inv_id,)).fetchone()
    if not row:
        conn.close()
        return
    new_state = 0 if row[0] else 1
    slot_col = {'cosmetic_aura': 'equipped_aura', 'cosmetic_body': 'equipped_body', 'title': 'equipped_title'}.get(category)
    if new_state == 1 and slot_col:
        conn.execute("UPDATE player_inventory SET equipped=0 WHERE item_key IN (SELECT item_key FROM shop_items WHERE category=?) AND id!=?", (category, inv_id))
        item_row = conn.execute("SELECT effect_value FROM shop_items WHERE item_key=?", (item_key,)).fetchone()
        conn.execute(f"UPDATE character_data SET {slot_col}=? WHERE id=1", (item_row[0] if item_row else '',))
    elif slot_col:
        conn.execute(f"UPDATE character_data SET {slot_col}='' WHERE id=1")
    conn.execute("UPDATE player_inventory SET equipped=? WHERE id=?", (new_state, inv_id))
    conn.commit()
    conn.close()


def use_item(inv_id):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("""
        SELECT pi.uses_remaining, si.effect_type, si.effect_value, si.name
        FROM player_inventory pi JOIN shop_items si ON si.item_key=pi.item_key WHERE pi.id=?
    """, (inv_id,)).fetchone()
    if not row:
        conn.close()
        return False, "Item nicht gefunden"
    uses, eff_type, eff_val, iname = row
    if uses == 0:
        conn.close()
        return False, "Keine Verwendungen mehr übrig"
    msg = ""
    if eff_type == 'xp_boost':
        expiry = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        conn.execute("UPDATE settings SET value=? WHERE key='xp_boost_expiry'", (expiry,))
        if not conn.execute("SELECT 1 FROM settings WHERE key='xp_boost_expiry'").fetchone():
            conn.execute("INSERT INTO settings VALUES ('xp_boost_expiry',?)", (expiry,))
        mult_key, mult_val = 'xp_boost_multiplier', eff_val
        conn.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (mult_key, mult_val))
        msg = f"⚡ XP-Boost aktiv! +{int((float(eff_val)-1)*100)}% XP für 24h"
    elif eff_type == 'streak_shield':
        conn.execute("INSERT OR REPLACE INTO settings VALUES ('streak_shield_active','1')")
        msg = "🛡️ Streak-Schild aktiv! Nächster verpasster Tag wird vergeben."
    elif eff_type == 'streak_heal':
        msg = "💚 Streak-Heiler verwendet. Dein Streak wurde um 1 Tag verlängert."
    elif eff_type == 'coin_boost_temp':
        expiry = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        conn.execute("INSERT OR REPLACE INTO settings VALUES ('coin_boost_expiry',?)", (expiry,))
        conn.execute("INSERT OR REPLACE INTO settings VALUES ('coin_boost_mult',?)", (eff_val,))
        msg = f"🪙 Doppelte Münzen aktiv für 24h!"
    else:
        msg = f"'{iname}' wurde verwendet."
    if uses > 0:
        conn.execute("UPDATE player_inventory SET uses_remaining=uses_remaining-1 WHERE id=?", (inv_id,))
        conn.execute("DELETE FROM player_inventory WHERE id=? AND uses_remaining<=0", (inv_id,))
    conn.commit()
    conn.close()
    return True, msg


def get_level_history():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT level_reached, coins_earned, achieved_at FROM level_ups ORDER BY level_reached DESC LIMIT 50").fetchall()
    conn.close()
    return rows


# ─── Habit Tracker DB ───────────────────────────────────────────

def get_habits(active_only=True):
    conn = sqlite3.connect(DB_PATH)
    q = "SELECT id, name, category, icon, color, sort_order, active FROM habits"
    if active_only:
        q += " WHERE active=1"
    rows = conn.execute(q + " ORDER BY sort_order, id").fetchall()
    conn.close()
    return [dict(zip(["id","name","category","icon","color","sort_order","active"], r)) for r in rows]


def add_habit(name, category="general", icon="⭐", color="#00d4ff"):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO habits (name,category,icon,color) VALUES (?,?,?,?)",
                  (name, category, icon, color))
    conn.commit()
    conn.close()


def delete_habit(habit_id):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM habits WHERE id=?", (habit_id,))
    conn.commit()
    conn.close()


def log_habit(habit_id, log_date, energy_level, completion_pct, notes=""):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO habit_logs (habit_id, log_date, energy_level, completion_pct, notes)
        VALUES (?,?,?,?,?)
        ON CONFLICT(habit_id, log_date) DO UPDATE SET
            energy_level=excluded.energy_level,
            completion_pct=excluded.completion_pct,
            notes=excluded.notes
    """, (habit_id, log_date, energy_level, completion_pct, notes))
    conn.commit()
    conn.close()


def get_habit_log(habit_id, log_date):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT id,habit_id,log_date,energy_level,completion_pct,notes FROM habit_logs WHERE habit_id=? AND log_date=?",
        (habit_id, log_date)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return dict(zip(["id","habit_id","log_date","energy_level","completion_pct","notes"], row))


def get_habit_logs_range(habit_id, days=84):
    conn = sqlite3.connect(DB_PATH)
    from_date = (date.today() - timedelta(days=days - 1)).isoformat()
    rows = conn.execute("""
        SELECT log_date, energy_level, completion_pct, notes FROM habit_logs
        WHERE habit_id=? AND log_date>=? ORDER BY log_date
    """, (habit_id, from_date)).fetchall()
    conn.close()
    return [dict(zip(["log_date","energy_level","completion_pct","notes"], r)) for r in rows]


def get_today_energy():
    val = get_setting(f"energy_{date.today().isoformat()}")
    return int(val) if val else 80


def set_today_energy(pct):
    set_setting(f"energy_{date.today().isoformat()}", str(int(pct)))


def get_weekday_stats():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT CAST(strftime('%w', completed_at) AS INTEGER) as wd,
               COUNT(*) as tasks, SUM(elapsed_seconds) as secs
        FROM entries WHERE done=1 AND completed_at IS NOT NULL
        GROUP BY wd ORDER BY wd
    """).fetchall()
    conn.close()
    return rows


def get_personal_records():
    conn = sqlite3.connect(DB_PATH)
    best_day = conn.execute("""
        SELECT DATE(completed_at) as d, COUNT(*) as n FROM entries
        WHERE done=1 AND completed_at IS NOT NULL
        GROUP BY d ORDER BY n DESC LIMIT 1
    """).fetchone()
    best_time_day = conn.execute("""
        SELECT DATE(completed_at) as d, SUM(elapsed_seconds) as s FROM entries
        WHERE done=1 AND completed_at IS NOT NULL
        GROUP BY d ORDER BY s DESC LIMIT 1
    """).fetchone()
    total_secs = conn.execute(
        "SELECT SUM(elapsed_seconds) FROM entries WHERE done=1"
    ).fetchone()[0] or 0
    longest = conn.execute("""
        SELECT content, elapsed_seconds FROM entries WHERE done=1 AND elapsed_seconds>0
        ORDER BY elapsed_seconds DESC LIMIT 1
    """).fetchone()
    active_days = conn.execute("""
        SELECT COUNT(DISTINCT DATE(completed_at)) FROM entries
        WHERE done=1 AND completed_at IS NOT NULL
        AND completed_at > datetime('now', '-30 days')
    """).fetchone()[0] or 0
    conn.close()
    return {
        'best_day': best_day, 'best_time_day': best_time_day,
        'total_hours': round(total_secs / 3600, 1),
        'longest': longest, 'active_days_30': active_days
    }


# ========== SAMPLE DATA / RESET ==========

def insert_sample_data():
    samples = [
        ("brain", "Gedanken: Heute an Projekt X denken", "sample_data", None),
        ("brain", "Idee: Microblog starten", "sample_data", None),
        ("highlight", "Wichtig: Erste Aufgabe für Projekt X", "sample_data",
         (date.today() + timedelta(days=1)).isoformat()),
        ("micro", "2 Minuten: E-Mail an Jonas schreiben", "sample_data",
         date.today().isoformat()),
        ("micro", "2 Minuten: Kurze Aufräumaktion Schreibtisch", "sample_data", None),
    ]
    for etype, content, tags, dl in samples:
        add_entry(etype, content, tags=tags, estimate=2, points=0, deadline=dl)


def delete_sample_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM entries WHERE tags LIKE '%sample_data%'")
    conn.commit()
    conn.close()


def delete_all_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM entries')
    conn.commit()
    conn.close()


# ========== PROJECTS ==========

PROJECT_COLORS = ["#60a5fa", "#f97316", "#4ade80", "#a78bfa", "#f43f5e", "#fbbf24", "#22d3ee"]


def get_projects():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, name, description, deadline, color, active, created_at, daily_minutes FROM projects ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    return rows


def add_project(name, description, deadline, color, daily_minutes):
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO projects (name, description, deadline, color, active, created_at, daily_minutes) VALUES (?,?,?,?,1,?,?)',
              (name, description, deadline, color, now, daily_minutes))
    pid = c.lastrowid
    conn.commit()
    conn.close()
    return pid


def delete_project(project_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM project_tasks WHERE project_id=?', (project_id,))
    c.execute('DELETE FROM projects WHERE id=?', (project_id,))
    conn.commit()
    conn.close()


def get_project_tasks(project_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT id, project_id, content, estimate_minutes, priority, done,
                        completed_at, scheduled_date, order_index, COALESCE(notes,''), COALESCE(highlight_color,'')
                 FROM project_tasks WHERE project_id=? ORDER BY order_index, id''', (project_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def add_project_task(project_id, content, estimate, priority=5):
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COALESCE(MAX(order_index),0) FROM project_tasks WHERE project_id=?', (project_id,))
    max_order = c.fetchone()[0]
    c.execute('''INSERT INTO project_tasks (project_id, content, estimate_minutes, priority, done, order_index, created_at)
                 VALUES (?,?,?,?,0,?,?)''', (project_id, content, estimate, priority, max_order + 1, now))
    conn.commit()
    conn.close()


def toggle_project_task_done(task_id, new_val):
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if new_val:
        c.execute('UPDATE project_tasks SET done=1, completed_at=? WHERE id=?', (now, task_id))
    else:
        c.execute('UPDATE project_tasks SET done=0, completed_at=NULL WHERE id=?', (task_id,))
    conn.commit()
    conn.close()


def delete_project_task(task_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM project_tasks WHERE id=?', (task_id,))
    conn.commit()
    conn.close()


def move_project_task(task_id, direction, project_id):
    """Move task up (-1) or down (+1) within its project."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    tasks = c.execute(
        "SELECT id, order_index FROM project_tasks WHERE project_id=? AND done=0 ORDER BY order_index, id",
        (project_id,)
    ).fetchall()
    ids = [r[0] for r in tasks]
    if task_id not in ids:
        conn.close()
        return
    idx = ids.index(task_id)
    swap = idx + direction
    if swap < 0 or swap >= len(ids):
        conn.close()
        return
    # Swap order_index values
    oi_a = tasks[idx][1]
    oi_b = tasks[swap][1]
    if oi_a == oi_b:
        oi_b = oi_a + 1
    c.execute("UPDATE project_tasks SET order_index=? WHERE id=?", (oi_b, task_id))
    c.execute("UPDATE project_tasks SET order_index=? WHERE id=?", (oi_a, ids[swap]))
    # Normalize order_index to 0,1,2...
    updated = c.execute(
        "SELECT id FROM project_tasks WHERE project_id=? AND done=0 ORDER BY order_index, id",
        (project_id,)
    ).fetchall()
    for i, (tid,) in enumerate(updated):
        c.execute("UPDATE project_tasks SET order_index=? WHERE id=?", (i, tid))
    conn.commit()
    conn.close()


def update_project_task_notes(task_id, notes):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE project_tasks SET notes=? WHERE id=?", (notes or '', task_id))
    conn.commit()
    conn.close()


def update_project_task(task_id, content, estimate, priority, notes, highlight_color, scheduled_date):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE project_tasks SET content=?, estimate_minutes=?, priority=?, notes=?, "
        "highlight_color=?, scheduled_date=? WHERE id=?",
        (content, estimate, priority, notes or '', highlight_color or '', scheduled_date or '', task_id)
    )
    conn.commit()
    conn.close()


def schedule_project_tasks(project_id):
    """Distribute undone tasks across days from today to deadline with 10% buffer."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT deadline, daily_minutes FROM projects WHERE id=?', (project_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return
    deadline_str, daily_mins = row
    daily_mins = max(daily_mins or 60, 15)
    try:
        deadline = date.fromisoformat(deadline_str)
    except Exception:
        conn.close()
        return

    today = date.today()
    days_total = max((deadline - today).days, 1)
    buffer_days = max(1, int(days_total * 0.10))
    end_date = deadline - timedelta(days=buffer_days)
    if end_date < today:
        end_date = deadline

    c.execute('''SELECT id, estimate_minutes FROM project_tasks
                 WHERE project_id=? AND done=0 ORDER BY priority DESC, order_index''', (project_id,))
    tasks = c.fetchall()

    current = today
    budget = daily_mins
    for task_id, estimate in tasks:
        estimate = max(estimate or 30, 5)
        # advance day if budget exhausted
        while budget < min(estimate, daily_mins) and current <= end_date:
            current += timedelta(days=1)
            budget = daily_mins
        target = min(current, end_date)
        c.execute('UPDATE project_tasks SET scheduled_date=? WHERE id=?', (target.isoformat(), task_id))
        budget -= estimate
        if budget <= 0:
            current += timedelta(days=1)
            budget = daily_mins

    conn.commit()
    conn.close()


def sync_project_tasks():
    """Auto-add today's scheduled project tasks to entries (once per day)."""
    today_str = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT pt.id, pt.content, pt.estimate_minutes, p.name
                 FROM project_tasks pt JOIN projects p ON pt.project_id=p.id
                 WHERE pt.scheduled_date=? AND pt.done=0 AND p.active=1''', (today_str,))
    tasks = c.fetchall()
    for task_id, content, estimate, project_name in tasks:
        c.execute('SELECT COUNT(*) FROM entries WHERE entry_date=? AND content=? AND tags LIKE ?',
                  (today_str, content, f'%projekt%'))
        if c.fetchone()[0] == 0:
            now = datetime.utcnow().isoformat()
            c.execute('''INSERT INTO entries (entry_type, content, tags, estimate_minutes, points, created_at, entry_date, last_modified)
                         VALUES (?,?,?,?,0,?,?,?)''',
                      ('brain', content, f'projekt,{project_name}', estimate or 30, now, today_str, now))
    conn.commit()
    conn.close()


# ========== CALISTHENICS TRAININGSSYSTEM ==========

def get_cal_progress():
    """Fortschritt je Track: {track: {level, consecutive_clean, bonus, best_reps}}."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT track, current_level, consecutive_clean, bonus_reps, best_reps FROM cal_progress").fetchall()
    conn.close()
    prog = {t: {'level': 0, 'consecutive_clean': 0, 'bonus': 0, 'best_reps': 0} for t in CAL_TRACKS}
    for track, lvl, cc, bonus, best in rows:
        if track in prog:
            prog[track] = {'level': lvl, 'consecutive_clean': cc, 'bonus': bonus, 'best_reps': best}
    return prog


def get_cal_exercise(track, level_idx=None, bonus=0):
    """Liefert die aktuelle Übung eines Tracks inkl. (ggf. unendlich wachsendem) Zielwert."""
    levels = CAL_TRACKS[track]['levels']
    if level_idx is None:
        level_idx = 0
    level_idx = max(0, min(level_idx, len(levels) - 1))
    base = levels[level_idx]
    is_max = level_idx == len(levels) - 1
    target_reps = base['reps'] + (bonus if is_max else 0)
    return {**base, 'target_reps': target_reps, 'level_idx': level_idx, 'is_max_level': is_max,
            'level_count': len(levels)}


def todays_skill_track():
    wd = date.today().weekday()  # 0=Montag
    return 'skill_handstand' if wd in (0, 2, 4, 6) else 'skill_muscleup'


def todays_cal_tracks():
    return ['push', 'pull', 'legs', 'core', todays_skill_track()]


def log_cal_session(track, sets_completed, best_reps, notes=''):
    """Loggt eine Trainingseinheit, erkennt Fortschritt und steigert das Level bei Bedarf."""
    prog_all = get_cal_progress()
    prog = prog_all[track]
    ex = get_cal_exercise(track, prog['level'], prog['bonus'])
    today_str = date.today().isoformat()
    now = datetime.utcnow().isoformat()

    clean = sets_completed >= ex['sets'] and best_reps >= ex['target_reps']

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO cal_sessions
                 (session_date, track, exercise_name, level_idx, sets_completed, target_sets,
                  best_reps, target_reps, is_hold, clean, notes, created_at)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
              (today_str, track, ex['name'], ex['level_idx'], sets_completed, ex['sets'],
               best_reps, ex['target_reps'], int(ex['hold']), int(clean), notes, now))

    new_cc = prog['consecutive_clean'] + 1 if clean else 0
    new_level = prog['level']
    new_bonus = prog['bonus']
    new_best = max(prog['best_reps'], best_reps)
    leveled_up = False
    new_level_name = None

    if new_cc >= 2:
        new_cc = 0
        if ex['is_max_level']:
            new_bonus += 2 if ex['hold'] else 1
        else:
            new_level += 1
            new_best = 0
        leveled_up = True
        next_ex = get_cal_exercise(track, new_level, new_bonus)
        new_level_name = next_ex['name']

    c.execute('''INSERT INTO cal_progress (track, current_level, consecutive_clean, bonus_reps, best_reps, updated_at)
                 VALUES (?,?,?,?,?,?)
                 ON CONFLICT(track) DO UPDATE SET
                   current_level=excluded.current_level,
                   consecutive_clean=excluded.consecutive_clean,
                   bonus_reps=excluded.bonus_reps,
                   best_reps=excluded.best_reps,
                   updated_at=excluded.updated_at''',
              (track, new_level, new_cc, new_bonus, new_best, now))
    conn.commit()
    conn.close()
    _schedule_backup()
    return {'clean': clean, 'leveled_up': leveled_up, 'new_level_name': new_level_name, 'exercise': ex}


def get_cal_streak():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT DISTINCT session_date FROM cal_sessions ORDER BY session_date").fetchall()
    conn.close()
    date_set = {r[0] for r in rows}
    if not date_set:
        return {'current': 0, 'longest': 0, 'trained_today': False, 'dates': date_set, 'total_sessions': 0}

    today = date.today()
    trained_today = today.isoformat() in date_set
    cur = 0
    d = today if trained_today else today - timedelta(days=1)
    while d.isoformat() in date_set:
        cur += 1
        d -= timedelta(days=1)

    sorted_dates = sorted(date.fromisoformat(x) for x in date_set)
    longest = 1
    run = 1
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1
    longest = max(longest, cur)

    conn = sqlite3.connect(DB_PATH)
    total_sessions = conn.execute("SELECT COUNT(*) FROM cal_sessions").fetchone()[0]
    conn.close()

    return {'current': cur, 'longest': longest, 'trained_today': trained_today,
            'dates': date_set, 'total_sessions': total_sessions}


def sync_daily_training():
    """Erstellt das heutige Trainings-Highlight im Kalender (einmal pro Tag, idempotent)."""
    today_str = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM entries WHERE entry_date=? AND tags LIKE '%training%'", (today_str,))
    if c.fetchone()[0] == 0:
        tracks = todays_cal_tracks()
        names = [CAL_TRACKS[t]['label'] for t in tracks]
        content = "🏋️ Calisthenics: " + ", ".join(names)
        now = datetime.utcnow().isoformat()
        c.execute('''INSERT INTO entries (entry_type, content, tags, priority, estimate_minutes, points, created_at, entry_date, last_modified)
                     VALUES (?,?,?,?,?,?,?,?,?)''',
                  ('highlight', content, 'training', 9, 20, 0, now, today_str, now))
        conn.commit()
    conn.close()


def get_todays_training_entry_id():
    today_str = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT id, done FROM entries WHERE entry_date=? AND tags LIKE '%training%' ORDER BY id DESC LIMIT 1",
                        (today_str,)).fetchone()
    conn.close()
    return row if row else (None, 0)


# ========== SCHLAFRYTHMUS & ROUTINEN ==========

def _sleep_scale(hhmm):
    """Wandelt 'HH:MM' in eine monoton steigende Skala ab 18:00 um (für Bettzeit-Rechnungen über Mitternacht)."""
    h, m = map(int, hhmm.split(':'))
    return ((h - 18) % 24) * 60 + m


def _sleep_unscale(scale):
    scale = int(scale) % 1440
    h = (18 + scale // 60) % 24
    m = scale % 60
    return f"{h:02d}:{m:02d}"


def get_sleep_target_bedtime():
    """Heutige Ziel-Bettzeit auf der Rampe Richtung 00:00 (10 Min/Tag früher, ausgehend von der Baseline)."""
    start_str = get_setting('sleep_program_start_date')
    baseline = get_setting('sleep_baseline_bedtime', '02:30')
    if not start_str:
        start_str = date.today().isoformat()
        set_setting('sleep_program_start_date', start_str)
    try:
        start_date = date.fromisoformat(start_str)
    except Exception:
        start_date = date.today()
    days_elapsed = max(0, (date.today() - start_date).days)
    baseline_scale = _sleep_scale(baseline)
    goal_scale = _sleep_scale(SLEEP_GOAL_BEDTIME)
    target_scale = max(goal_scale, baseline_scale - SLEEP_RAMP_STEP_MINUTES * days_elapsed)
    reached_goal = target_scale <= goal_scale
    total_steps = max(1, math.ceil((baseline_scale - goal_scale) / SLEEP_RAMP_STEP_MINUTES))
    days_to_goal = max(0, total_steps - days_elapsed)
    progress_pct = int(round(min(100, days_elapsed / total_steps * 100)))
    return {
        'target_time': _sleep_unscale(target_scale),
        'baseline': baseline,
        'days_elapsed': days_elapsed,
        'reached_goal': reached_goal,
        'days_to_goal': days_to_goal,
        'progress_pct': progress_pct,
    }


def get_routine_checks(log_date, routine_type):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT task_key, done FROM routine_checks WHERE log_date=? AND routine=?",
        (log_date, routine_type)
    ).fetchall()
    conn.close()
    return {k: bool(d) for k, d in rows}


def set_routine_check(log_date, routine_type, task_key, done):
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''INSERT INTO routine_checks (log_date, routine, task_key, done, created_at)
                     VALUES (?,?,?,?,?)
                     ON CONFLICT(log_date, routine, task_key) DO UPDATE SET done=excluded.done''',
                 (log_date, routine_type, task_key, int(done), now))
    conn.commit()
    conn.close()
    _schedule_backup()


def routine_adherence(log_date, routine_type):
    tasks = EVENING_ROUTINE_TASKS if routine_type == 'evening' else MORNING_ROUTINE_TASKS
    checks = get_routine_checks(log_date, routine_type)
    done = sum(1 for t in tasks if checks.get(t['key']))
    return done / len(tasks)


def log_sleep(log_date, quality_pct, bedtime=None, wake_time=None, notes=''):
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''INSERT INTO sleep_logs (log_date, quality_pct, bedtime, wake_time, notes, created_at)
                     VALUES (?,?,?,?,?,?)
                     ON CONFLICT(log_date) DO UPDATE SET
                       quality_pct=excluded.quality_pct, bedtime=excluded.bedtime,
                       wake_time=excluded.wake_time, notes=excluded.notes''',
                 (log_date, quality_pct, bedtime, wake_time, notes, now))
    conn.commit()
    conn.close()
    _schedule_backup()


def get_sleep_log(log_date):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT quality_pct, bedtime, wake_time, notes FROM sleep_logs WHERE log_date=?", (log_date,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {'quality_pct': row[0], 'bedtime': row[1], 'wake_time': row[2], 'notes': row[3]}


def get_routine_streak(routine_type):
    """Streak voller (100%) Tage für eine Routine."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT log_date, SUM(done), COUNT(*) FROM routine_checks WHERE routine=? GROUP BY log_date",
        (routine_type,)
    ).fetchall()
    conn.close()
    total_tasks = len(EVENING_ROUTINE_TASKS if routine_type == 'evening' else MORNING_ROUTINE_TASKS)
    full_dates = {d for d, done_sum, cnt in rows if cnt >= total_tasks and (done_sum or 0) >= total_tasks}

    if not full_dates:
        return {'current': 0, 'longest': 0, 'dates': full_dates}

    today = date.today()
    cur = 0
    d = today if today.isoformat() in full_dates else today - timedelta(days=1)
    while d.isoformat() in full_dates:
        cur += 1
        d -= timedelta(days=1)

    sorted_dates = sorted(date.fromisoformat(x) for x in full_dates)
    longest = run = 1
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1
    longest = max(longest, cur)
    return {'current': cur, 'longest': longest, 'dates': full_dates}


def _daily_productivity_series(start_date, end_date):
    """date_str -> {completion_rate, points, tasks_done, first_action_min}, aus echten entries-Daten."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT entry_date, done, points, started_at, completed_at FROM entries "
        "WHERE entry_date BETWEEN ? AND ?", (start_date.isoformat(), end_date.isoformat())
    ).fetchall()
    conn.close()
    agg = {}
    for entry_date, done, points, started_at, completed_at in rows:
        a = agg.setdefault(entry_date, {'total': 0, 'done': 0, 'points': 0, 'first_ts': None})
        a['total'] += 1
        a['done'] += done or 0
        a['points'] += points or 0
        ts = started_at or completed_at
        if ts:
            try:
                t = datetime.fromisoformat(ts)
                if a['first_ts'] is None or t < a['first_ts']:
                    a['first_ts'] = t
            except Exception:
                pass
    out = {}
    for d, a in agg.items():
        first_min = (a['first_ts'].hour * 60 + a['first_ts'].minute) if a['first_ts'] else None
        out[d] = {
            'completion_rate': a['done'] / a['total'] if a['total'] else 0,
            'points': a['points'],
            'tasks_done': a['done'],
            'first_action_min': first_min,
        }
    return out


def _routine_adherence_map(routine_type):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT log_date, SUM(done), COUNT(*) FROM routine_checks WHERE routine=? GROUP BY log_date",
        (routine_type,)
    ).fetchall()
    conn.close()
    total_tasks = len(EVENING_ROUTINE_TASKS if routine_type == 'evening' else MORNING_ROUTINE_TASKS)
    return {d: (done_sum or 0) / total_tasks for d, done_sum, cnt in rows}


def _sleep_quality_map(start_date, end_date):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT log_date, quality_pct FROM sleep_logs WHERE log_date BETWEEN ? AND ? AND quality_pct IS NOT NULL",
        (start_date.isoformat(), end_date.isoformat())
    ).fetchall()
    conn.close()
    return {d: q for d, q in rows}


def analyze_routine_patterns(min_n=3):
    """Echte Mustererkennung: vergleicht Tage mit vollständiger Routine/guter Schlafqualität gegen den Rest,
    basierend auf den tatsächlichen entries-Daten. Liefert None pro Vergleich wenn die Datenlage zu dünn ist."""
    today = date.today()
    start = today - timedelta(days=60)
    prod = _daily_productivity_series(start, today)
    morning_adh = _routine_adherence_map('morning')
    evening_adh = _routine_adherence_map('evening')
    sleep_q = _sleep_quality_map(start, today)

    def split(adh_map, shift_days, metric):
        hi, lo = [], []
        for d_str, adh in adh_map.items():
            try:
                d = date.fromisoformat(d_str)
            except Exception:
                continue
            target = (d + timedelta(days=shift_days)).isoformat()
            p = prod.get(target)
            if not p or p.get(metric) is None:
                continue
            (hi if adh >= 0.999 else lo).append(p[metric])
        return hi, lo

    def avg(lst):
        return sum(lst) / len(lst) if lst else None

    results = {}

    hi, lo = split(morning_adh, 0, 'completion_rate')
    results['morning_completion'] = (
        {'hi_avg': avg(hi) * 100, 'lo_avg': avg(lo) * 100, 'n_hi': len(hi), 'n_lo': len(lo)}
        if len(hi) >= min_n and len(lo) >= min_n else None
    )

    hi, lo = split(evening_adh, 1, 'completion_rate')
    results['evening_next_completion'] = (
        {'hi_avg': avg(hi) * 100, 'lo_avg': avg(lo) * 100, 'n_hi': len(hi), 'n_lo': len(lo)}
        if len(hi) >= min_n and len(lo) >= min_n else None
    )

    hi, lo = split(morning_adh, 0, 'first_action_min')
    results['speed'] = (
        {'hi_avg': avg(hi), 'lo_avg': avg(lo), 'n_hi': len(hi), 'n_lo': len(lo)}
        if len(hi) >= min_n and len(lo) >= min_n else None
    )

    sq_hi, sq_lo = [], []
    for d_str, q in sleep_q.items():
        p = prod.get(d_str)
        if not p:
            continue
        (sq_hi if q >= 75 else sq_lo).append(p['completion_rate'])
    results['sleep_quality'] = (
        {'hi_avg': avg(sq_hi) * 100, 'lo_avg': avg(sq_lo) * 100, 'n_hi': len(sq_hi), 'n_lo': len(sq_lo)}
        if len(sq_hi) >= min_n and len(sq_lo) >= min_n else None
    )

    return results


# ========== HAUSHALT ==========

def log_household_task(task_key, log_date=None):
    log_date = log_date or date.today().isoformat()
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''INSERT INTO household_log (task_key, log_date, created_at)
                     VALUES (?,?,?)
                     ON CONFLICT(task_key, log_date) DO NOTHING''', (task_key, log_date, now))
    conn.commit()
    conn.close()
    _schedule_backup()


def unlog_household_task(task_key, log_date=None):
    log_date = log_date or date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM household_log WHERE task_key=? AND log_date=?", (task_key, log_date))
    conn.commit()
    conn.close()
    _schedule_backup()


def get_household_status():
    """Für jede Haushaltsaufgabe: zuletzt erledigt, Tage seitdem, fällig/überfällig, Dringlichkeit."""
    today = date.today()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT task_key, MAX(log_date) FROM household_log GROUP BY task_key").fetchall()
    conn.close()
    last_done_map = {k: v for k, v in rows}

    out = []
    for t in HOUSEHOLD_TASKS:
        last_done = last_done_map.get(t['key'])
        interval = HOUSEHOLD_FREQUENCY_DAYS[t['frequency']]
        if last_done:
            days_since = (today - date.fromisoformat(last_done)).days
        else:
            days_since = interval * 3  # nie gemacht -> klar überfällig, aber kein absurder Wert
        due = days_since >= interval
        overdue = days_since >= interval * 1.5
        urgency = min(1.5, days_since / interval) if interval else 0
        out.append({
            **t, 'last_done': last_done, 'days_since': days_since,
            'due': due, 'overdue': overdue, 'urgency': urgency,
        })
    return out


def household_clean_score():
    """Wohnung-Sauber-Score 0-100: Durchschnitt der 'Frische' aller Aufgaben relativ zu ihrem Intervall."""
    status = get_household_status()
    if not status:
        return 100
    freshness_vals = []
    for t in status:
        interval = HOUSEHOLD_FREQUENCY_DAYS[t['frequency']]
        freshness = max(0.0, 1 - t['days_since'] / (interval * 1.5))
        freshness_vals.append(freshness)
    return int(round(sum(freshness_vals) / len(freshness_vals) * 100))


def get_household_daily_streak():
    daily_keys = [t['key'] for t in HOUSEHOLD_TASKS if t['frequency'] == 'daily']
    if not daily_keys:
        return {'current': 0, 'longest': 0}
    placeholders = ",".join("?" * len(daily_keys))
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        f"SELECT log_date, COUNT(DISTINCT task_key) FROM household_log "
        f"WHERE task_key IN ({placeholders}) GROUP BY log_date",
        daily_keys
    ).fetchall()
    conn.close()
    full_dates = {d for d, cnt in rows if cnt >= len(daily_keys)}
    if not full_dates:
        return {'current': 0, 'longest': 0}

    today = date.today()
    cur = 0
    d = today if today.isoformat() in full_dates else today - timedelta(days=1)
    while d.isoformat() in full_dates:
        cur += 1
        d -= timedelta(days=1)

    sorted_dates = sorted(date.fromisoformat(x) for x in full_dates)
    longest = run = 1
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1
    longest = max(longest, cur)
    return {'current': cur, 'longest': longest}


def household_wohlfuehl_index():
    """Kombiniert den Sauber-Score mit der Konsistenz der täglichen Mini-Routine."""
    clean = household_clean_score()
    streak = get_household_daily_streak()
    consistency_bonus = min(20, streak['current'] * 2)
    return min(100, int(round(clean * 0.8 + consistency_bonus)))


def get_today_workload():
    """Heutige Aufgabenlast — Grundlage für ein realistisches Haushalts-Zeitbudget."""
    today_str = date.today().isoformat()
    rows = get_today_entries()
    undone = [r for r in rows if not r[9]]
    total_estimate = sum((r[5] or 0) for r in undone)
    deadlines_today = sum(1 for r in undone if r[13] == today_str)
    return {
        'undone_count': len(undone),
        'total_estimate': total_estimate,
        'deadlines_today': deadlines_today,
    }


def household_time_budget(workload=None):
    """Wie viele Minuten Haushalt sind heute realistisch — abhängig von Deadlines/Workload.
    An vollen Tagen (viele Deadlines/hoher geschätzter Aufwand) bleibt nur Zeit für Mini-Tasks."""
    workload = workload or get_today_workload()
    score = workload['deadlines_today'] * 2 + workload['undone_count']
    if score >= 8 or workload['total_estimate'] >= 360:
        return 10
    elif score >= 4 or workload['total_estimate'] >= 180:
        return 25
    else:
        return 60


def suggest_household_break_tasks():
    """Wählt fällige Haushaltsaufgaben passend zum heutigen, Deadline-bewussten Zeitbudget aus."""
    status = get_household_status()
    workload = get_today_workload()
    budget = household_time_budget(workload)
    due = [t for t in status if t['due']]
    due.sort(key=lambda t: (-t['urgency'], t['est_minutes']))

    picked, used = [], 0
    for t in due:
        if used + t['est_minutes'] <= budget:
            picked.append(t)
            used += t['est_minutes']

    return {'tasks': picked, 'budget_minutes': budget, 'used_minutes': used, 'workload': workload}


def _household_heatmap_html(days=60):
    """Konsistenz-Heatmap der täglichen Haushalts-Mini-Routine (Anteil erledigter Daily-Tasks pro Tag)."""
    daily_keys = [t['key'] for t in HOUSEHOLD_TASKS if t['frequency'] == 'daily']
    today_d = date.today()
    conn = sqlite3.connect(DB_PATH)
    placeholders = ",".join("?" * len(daily_keys))
    rows = conn.execute(
        f"SELECT log_date, COUNT(DISTINCT task_key) FROM household_log "
        f"WHERE task_key IN ({placeholders}) GROUP BY log_date",
        daily_keys
    ).fetchall() if daily_keys else []
    conn.close()
    frac_map = {d: cnt / len(daily_keys) for d, cnt in rows} if daily_keys else {}

    color = "#2ecc71"

    def cell_color(frac):
        if not frac:
            return "rgba(255,255,255,0.05)"
        if frac >= 1:
            return color
        if frac >= 0.5:
            return f"{color}88"
        return f"{color}44"

    cells = ""
    for i in range(days - 1, -1, -1):
        d = today_d - timedelta(days=i)
        frac = frac_map.get(d.isoformat())
        tip = f"{d.strftime('%d.%m')}: {int((frac or 0) * 100)}%"
        cells += f'<div title="{tip}" style="width:14px;height:14px;background:{cell_color(frac)};border-radius:2px;flex-shrink:0"></div>'

    return f"""<div style="background:rgba(255,255,255,0.03);border-radius:12px;padding:14px 16px;
  border:1px solid rgba(255,255,255,0.07)">
  <div style="font-size:12px;font-weight:700;color:white;margin-bottom:8px">🏡 Tägliche Haushalts-Routine</div>
  <div style="display:flex;flex-wrap:wrap;gap:3px;width:calc(14*(14px + 3px))">
    {cells}
  </div>
</div>"""


# ========== SPONTANE GEDANKEN ==========

def add_spontaneous_thought(content):
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO spontaneous_thoughts (content, created_at, sorted) VALUES (?,?,0)",
              (content.strip(), now))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    _schedule_backup()
    return new_id


def get_unsorted_thoughts():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, content, created_at FROM spontaneous_thoughts WHERE sorted=0 ORDER BY created_at"
    ).fetchall()
    conn.close()
    return [{'id': r[0], 'content': r[1], 'created_at': r[2]} for r in rows]


def get_unsorted_thought_count():
    conn = sqlite3.connect(DB_PATH)
    n = conn.execute("SELECT COUNT(*) FROM spontaneous_thoughts WHERE sorted=0").fetchone()[0]
    conn.close()
    return n


def resolve_thought_to_entry(thought_id, content, entry_date):
    """Verwandelt einen spontanen Gedanken in eine echte To-Do-Aufgabe an entry_date."""
    new_id = add_entry("brain", content, estimate=10, entry_date=entry_date)
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE spontaneous_thoughts SET sorted=1, sorted_at=?, resolution=?, entry_id=? WHERE id=?",
        (now, f"todo:{entry_date}", new_id, thought_id)
    )
    conn.commit()
    conn.close()
    _schedule_backup()
    return new_id


def discard_thought(thought_id):
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE spontaneous_thoughts SET sorted=1, sorted_at=?, resolution='discarded' WHERE id=?",
        (now, thought_id)
    )
    conn.commit()
    conn.close()
    _schedule_backup()


def _render_spontan_bubble():
    """Permanent schwebende Post-it-Bubble zum spontanen Festhalten von Gedanken — auf jeder Seite sichtbar."""
    st.markdown("""
<style>
div.st-key-spontan_bubble_fab {
    position: fixed;
    bottom: 22px;
    right: 22px;
    z-index: 999999;
    width: auto !important;
}
div.st-key-spontan_bubble_fab button {
    border-radius: 50% !important;
    width: 54px !important;
    height: 54px !important;
    min-width: 54px !important;
    padding: 0 !important;
    font-size: 20px !important;
    box-shadow: 0 4px 18px rgba(0,0,0,0.45) !important;
    background: linear-gradient(135deg,#00d4ff 0%,#a29bfe 100%) !important;
    border: none !important;
    color: #0a0a0a !important;
}
</style>
""", unsafe_allow_html=True)

    unsorted_n = get_unsorted_thought_count()
    label = f"💭 {unsorted_n}" if unsorted_n else "💭"
    nonce = st.session_state.get('spontan_nonce', 0)

    with st.container(key="spontan_bubble_fab"):
        with st.popover(label, key="spontan_popover"):
            st.markdown("**💭 Spontaner Gedanke**")
            txt = st.text_area(
                "Gedanke", key=f"spontan_input_{nonce}", label_visibility="collapsed",
                placeholder="Kurz notieren, abends sortieren …", height=80
            )
            if st.button("✅ Ablegen", key="spontan_save", use_container_width=True):
                if txt and txt.strip():
                    add_spontaneous_thought(txt.strip())
                    st.session_state['spontan_nonce'] = nonce + 1
                    st.toast("Notiert — abends sortieren 📥", icon="💭")
                    st.rerun()
            if unsorted_n:
                st.caption(f"📥 {unsorted_n} ungesortiert — auf der Start-Seite einsortieren")


# ========== RECURRING TASKS ==========

DAY_ABBR = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

RECURRENCE_PRESETS = {
    "Täglich":              "0,1,2,3,4,5,6",
    "Wochentage (Mo–Fr)":   "0,1,2,3,4",
    "Wochenende":           "5,6",
    "Benutzerdefiniert":    None,
}

TIME_ICONS = {"morgen": "🌅", "abend": "🌙", "anytime": "📋"}
TIME_LABELS = {"morgen": "Morgen-Routine", "abend": "Abend-Routine", "anytime": "Aufgaben"}


def format_recurrence(rec_str):
    for label, val in RECURRENCE_PRESETS.items():
        if val == rec_str:
            return label
    days = [int(d) for d in rec_str.split(',') if d.strip().isdigit()]
    return ", ".join(DAY_ABBR[d] for d in sorted(days) if 0 <= d <= 6)


def get_recurring_tasks():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, entry_type, content, tags, estimate_minutes, recurrence, time_of_day, active, last_generated FROM recurring_tasks ORDER BY time_of_day, id')
    rows = c.fetchall()
    conn.close()
    return rows


def add_recurring_task(entry_type, content, tags, estimate, recurrence, time_of_day):
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO recurring_tasks (entry_type, content, tags, estimate_minutes, recurrence, time_of_day, active, created_at)
                 VALUES (?,?,?,?,?,?,1,?)''',
              (entry_type, content, tags or "", estimate, recurrence, time_of_day, now))
    conn.commit()
    conn.close()


def delete_recurring_task(rt_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM recurring_tasks WHERE id=?', (rt_id,))
    conn.commit()
    conn.close()


def toggle_recurring_active(rt_id, new_val):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE recurring_tasks SET active=? WHERE id=?', (1 if new_val else 0, rt_id))
    conn.commit()
    conn.close()


def sync_recurring_tasks():
    """Auto-generate today's entries from active recurring tasks (runs once per day)."""
    today = date.today()
    today_str = today.isoformat()
    weekday = today.weekday()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, entry_type, content, tags, estimate_minutes, recurrence, time_of_day, last_generated FROM recurring_tasks WHERE active=1')
    recurring = c.fetchall()

    for rt in recurring:
        rt_id, etype, content, tags, estimate, recurrence, time_of_day, last_generated = rt
        if last_generated == today_str:
            continue
        try:
            days = [int(d) for d in recurrence.split(',') if d.strip().isdigit()]
        except Exception:
            continue
        if weekday not in days:
            continue

        full_tags = f"routine,{time_of_day}" if time_of_day != "anytime" else "routine"
        if tags:
            full_tags = f"{full_tags},{tags}"

        c.execute('SELECT COUNT(*) FROM entries WHERE entry_date=? AND content=? AND tags LIKE ?',
                  (today_str, content, '%routine%'))
        if c.fetchone()[0] == 0:
            now = datetime.utcnow().isoformat()
            c.execute('''INSERT INTO entries (entry_type, content, tags, estimate_minutes, points, created_at, entry_date, last_modified)
                         VALUES (?,?,?,?,0,?,?,?)''',
                      (etype, content, full_tags, estimate, now, today_str, now))

        c.execute('UPDATE recurring_tasks SET last_generated=? WHERE id=?', (today_str, rt_id))

    conn.commit()
    conn.close()


# ========== GIST SYNC ==========

def gist_save(token, gist_id, data_dict):
    url = f"https://api.github.com/gists/{gist_id}"
    r = requests.patch(url, json={"files": {"kaizen.json": {"content": data_dict}}},
                       headers={"Authorization": f"token {token}"})
    return r.status_code, r.text


def gist_create(token, data_dict, description="Kaizen export"):
    url = "https://api.github.com/gists"
    r = requests.post(url, json={"files": {"kaizen.json": {"content": data_dict}},
                                  "description": description, "public": False},
                      headers={"Authorization": f"token {token}"})
    return r.status_code, r.json()


# ── Auto-Backup / Restore (vollständige SQLite DB via Gist) ─────

def _get_backup_credentials():
    """Returns (token, gist_id) from Streamlit secrets or DB settings. Both may be None."""
    token   = None
    gist_id = None
    try:
        import streamlit as _st
        token   = _st.secrets.get("GITHUB_BACKUP_TOKEN") or _st.secrets.get("github_backup_token")
        gist_id = _st.secrets.get("GITHUB_BACKUP_GIST_ID") or _st.secrets.get("github_backup_gist_id")
    except Exception:
        pass
    if not token:
        token = get_setting("backup_github_token", "")
    if not gist_id:
        gist_id = get_setting("backup_gist_id", "")
    return token or None, gist_id or None


def auto_backup_db():
    """Upload full SQLite DB as base64 to Gist. Silent on error."""
    try:
        token, gist_id = _get_backup_credentials()
        if not token:
            return False
        import base64
        with open(DB_PATH, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        payload = json.dumps({"v": 2, "db": b64, "ts": datetime.utcnow().isoformat()})
        headers = {"Authorization": f"token {token}"}
        if gist_id:
            r = requests.patch(
                f"https://api.github.com/gists/{gist_id}",
                json={"files": {"kaizen_db_backup.json": {"content": payload}}},
                headers=headers, timeout=10
            )
            if r.status_code in (200, 201):
                set_setting("last_backup", datetime.utcnow().isoformat())
                return True
        else:
            r = requests.post(
                "https://api.github.com/gists",
                json={"files": {"kaizen_db_backup.json": {"content": payload}},
                      "description": "Kaizen DB auto-backup", "public": False},
                headers=headers, timeout=10
            )
            if r.status_code == 201:
                new_id = r.json().get("id", "")
                set_setting("backup_gist_id", new_id)
                set_setting("last_backup", datetime.utcnow().isoformat())
                return True
        return False
    except Exception:
        return False


def auto_restore_db():
    """Restore DB from Gist if local DB is empty. Called once at startup."""
    try:
        token, gist_id = _get_backup_credentials()
        if not token or not gist_id:
            return False
        import base64
        r = requests.get(
            f"https://api.github.com/gists/{gist_id}",
            headers={"Authorization": f"token {token}"}, timeout=10
        )
        if r.status_code != 200:
            return False
        files = r.json().get("files", {})
        backup_file = files.get("kaizen_db_backup.json")
        if not backup_file:
            return False
        raw = backup_file.get("content", "")
        data = json.loads(raw)
        if data.get("v") != 2 or not data.get("db"):
            return False
        db_bytes = base64.b64decode(data["db"])
        with open(DB_PATH, "wb") as f:
            f.write(db_bytes)
        return True
    except Exception:
        return False


# ========== KI COACH ==========

def build_ai_context(days_back=0):
    today_str = date.today().isoformat()
    today_name = WOCHENTAGE[date.today().weekday()]
    period_start = (date.today() - timedelta(days=days_back)).isoformat() if days_back > 0 else today_str
    tomorrow_str = (date.today() + timedelta(days=1)).isoformat()
    next_week_str = (date.today() + timedelta(days=7)).isoformat()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''SELECT entry_date, entry_type, content, done, elapsed_seconds, tags, deadline, points
                 FROM entries WHERE entry_date >= ? AND entry_date <= ? ORDER BY entry_date, id''',
              (period_start, today_str))
    period_entries = c.fetchall()

    c.execute('''SELECT entry_date, COUNT(*) as total, SUM(done) as done_count, SUM(elapsed_seconds) as total_sec
                 FROM entries WHERE entry_date >= ? AND entry_date <= ?
                 GROUP BY entry_date ORDER BY entry_date''', (period_start, today_str))
    daily_stats = c.fetchall()

    c.execute('''SELECT entry_type, COUNT(*), SUM(done), AVG(elapsed_seconds)
                 FROM entries WHERE entry_date >= ? AND entry_date <= ?
                 GROUP BY entry_type''', (period_start, today_str))
    type_stats = c.fetchall()

    c.execute('''SELECT tags, COUNT(*) as cnt, SUM(done) as done_cnt
                 FROM entries WHERE entry_date >= ? AND entry_date <= ?
                 AND done=1 AND tags!='' AND tags IS NOT NULL
                 GROUP BY tags ORDER BY cnt DESC LIMIT 8''', (period_start, today_str))
    tag_stats = c.fetchall()

    c.execute('''SELECT content, deadline FROM entries
                 WHERE done=0 AND deadline!='' AND deadline IS NOT NULL AND deadline < ?
                 ORDER BY deadline''', (today_str,))
    overdue = c.fetchall()

    c.execute('''SELECT content, deadline FROM entries
                 WHERE done=0 AND deadline!='' AND deadline IS NOT NULL
                 AND deadline >= ? AND deadline <= ? ORDER BY deadline''', (tomorrow_str, next_week_str))
    upcoming = c.fetchall()

    c.execute('SELECT id, name, deadline, daily_minutes FROM projects WHERE active=1 ORDER BY deadline')
    projects = c.fetchall()
    project_infos = []
    for pid, pname, pdeadline, daily_mins in projects:
        c.execute('SELECT COUNT(*), SUM(done) FROM project_tasks WHERE project_id=?', (pid,))
        row = c.fetchone()
        total = row[0] or 0
        done_cnt = int(row[1] or 0)
        pct = int(done_cnt / total * 100) if total else 0
        c.execute('SELECT content FROM project_tasks WHERE project_id=? AND done=0 ORDER BY priority DESC, order_index LIMIT 1', (pid,))
        next_row = c.fetchone()
        project_infos.append((pname, pdeadline, total, done_cnt, pct, next_row[0] if next_row else None))

    c.execute('SELECT COUNT(*), SUM(done), SUM(elapsed_seconds), SUM(points) FROM entries')
    at = c.fetchone()
    at_total, at_done, at_sec, at_pts = at[0] or 0, at[1] or 0, at[2] or 0, at[3] or 0

    c.execute('SELECT COUNT(*) FROM recurring_tasks WHERE active=1')
    active_routines = c.fetchone()[0]

    conn.close()

    level, progress, level_step = get_level_and_progress()
    insights = get_ki_insights(limit=15)

    total_period = sum(r[1] for r in daily_stats)
    done_period = sum(int(r[2] or 0) for r in daily_stats)
    time_period_min = int(sum(int(r[3] or 0) for r in daily_stats) / 60)

    lines = []
    if days_back == 0:
        lines.append(f"## Heute — {today_name}, {today_str}\n")
    else:
        lines.append(f"## Zeitraum: {period_start} bis {today_str} ({days_back + 1} Tage)\n")

    lines.append(f"**Zeitraum:** {done_period}/{total_period} Aufgaben erledigt | {time_period_min} Min investiert")
    lines.append(f"**All-Time:** {at_done}/{at_total} Aufgaben | {int(at_sec/60)} Min | {at_pts} Punkte gesamt")
    lines.append(f"**Level {level}** ({progress}/{level_step} bis nächstes) | {active_routines} aktive Routinen\n")

    if days_back == 0:
        today_entries_flat = [(e[1], e[2], e[3], e[6]) for e in period_entries]
        today_open = [(e[0], e[1], e[3]) for e in today_entries_flat if not e[2]]
        today_done_list = [(e[0], e[1]) for e in today_entries_flat if e[2]]
        if today_open:
            lines.append("**Offen heute:**")
            for etype, content, dl in today_open:
                dl_info = f" ⏰ {dl}" if dl else ""
                lines.append(f"- [{TYPE_LABELS.get(etype, etype).split()[-1]}] {content}{dl_info}")
        if today_done_list:
            lines.append("**Heute erledigt:**")
            for etype, content in today_done_list:
                lines.append(f"- ✅ {content}")
        lines.append("")

    if days_back > 0 and len(daily_stats) > 1:
        lines.append("**Tagesweise:**")
        for day, total, done_c, elapsed_sec in daily_stats:
            done_c = done_c or 0
            rate = int(done_c / total * 100) if total else 0
            lines.append(f"- {day}: {done_c}/{total} ({rate}%), {int((elapsed_sec or 0)/60)} min")
        lines.append("")

    if type_stats:
        lines.append("**Aufgabentypen:**")
        for etype, cnt, done_c, avg_sec in type_stats:
            done_c = done_c or 0
            rate = int(done_c / cnt * 100) if cnt else 0
            lines.append(f"- {TYPE_LABELS.get(etype, etype)}: {done_c}/{cnt} ({rate}%), Ø {int((avg_sec or 0)/60)} min")
        lines.append("")

    if tag_stats:
        lines.append("**Top Tags:**")
        for tags, cnt, done_c in tag_stats[:5]:
            lines.append(f"- {tags}: {done_c or 0}/{cnt} erledigt")
        lines.append("")

    if overdue:
        lines.append(f"⚠️ **ÜBERFÄLLIG ({len(overdue)}):**")
        for content, dl in overdue:
            try:
                d = (date.today() - date.fromisoformat(dl)).days
                lines.append(f"- {content} (seit {d} Tagen, war fällig: {dl})")
            except Exception:
                lines.append(f"- {content} (Deadline: {dl})")
        lines.append("")

    if upcoming:
        lines.append("📅 **Demnächst fällig:**")
        for content, dl in upcoming:
            try:
                d = (date.fromisoformat(dl) - date.today()).days
                lines.append(f"- {content} (in {d} Tagen, {dl})")
            except Exception:
                lines.append(f"- {content} (Deadline: {dl})")
        lines.append("")

    if project_infos:
        lines.append("**Projekte:**")
        for pname, pdeadline, total, done_cnt, pct, next_task in project_infos:
            _, _, urg_label, _ = get_urgency(pdeadline)
            line = f"- {pname}: {done_cnt}/{total} ({pct}%)"
            if pdeadline:
                line += f" | Deadline: {pdeadline} {urg_label}"
            if next_task:
                line += f" | Nächstes: {next_task}"
            lines.append(line)
        lines.append("")

    if insights:
        lines.append("**Gelernte Muster über den Nutzer:**")
        for cat, ins, _ in insights:
            lines.append(f"- [{cat}] {ins}")

    return "\n".join(lines)


def save_review(review_type, content, review_date):
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO reviews (review_type, content, review_date, created_at) VALUES (?,?,?,?)',
              (review_type, content, review_date, now))
    conn.commit()
    conn.close()


def get_reviews(review_type, limit=5):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, content, review_date, created_at FROM reviews WHERE review_type=? ORDER BY created_at DESC LIMIT ?',
              (review_type, limit))
    rows = c.fetchall()
    conn.close()
    return rows


def save_ki_insight(category, insight):
    norm = insight.strip().lower()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id FROM ki_insights WHERE LOWER(insight)=?', (norm,))
    if not c.fetchone():
        now = datetime.utcnow().isoformat()
        c.execute('INSERT INTO ki_insights (category, insight, created_at) VALUES (?,?,?)',
                  (category, insight.strip(), now))
        conn.commit()
    conn.close()


def get_ki_insights(limit=20):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT category, insight, created_at FROM ki_insights ORDER BY created_at DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
KIMI_MODEL = "moonshotai/kimi-k2.6"


def _ki_stream(client, messages, placeholder, max_tokens=512):
    """Stream from NVIDIA/Kimi API. Handles empty chunks (IndexError fix)."""
    full_text = ""
    stream = client.chat.completions.create(
        model=KIMI_MODEL, messages=messages, max_tokens=max_tokens, stream=True
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            full_text += chunk.choices[0].delta.content
            placeholder.markdown(full_text + "▌")
    placeholder.markdown(full_text)
    return full_text


def _extract_and_save_insights(client, review_text):
    """Extract lasting insights about the user from a review (best-effort, silent on error)."""
    try:
        resp = client.chat.completions.create(
            model=KIMI_MODEL,
            messages=[
                {"role": "system", "content": "Du extrahierst Erkenntnisse. Antworte NUR im exakten Format, keine weiteren Texte."},
                {"role": "user", "content": (
                    "Extrahiere 2-4 langfristige Erkenntnisse über diesen Nutzer.\n"
                    "Format (eine pro Zeile, kein Zusatztext):\n"
                    "[MUSTER] Beobachtung\n[STÄRKE] Beobachtung\n[HERAUSFORDERUNG] Beobachtung\n\n"
                    f"Review:\n{review_text[:2000]}"
                )}
            ],
            max_tokens=200,
            stream=False
        )
        for line in resp.choices[0].message.content.strip().split("\n"):
            line = line.strip()
            if line.startswith("[") and "]" in line:
                end = line.index("]")
                cat = line[1:end].strip()
                insight = line[end + 1:].strip()
                if len(insight) > 5:
                    save_ki_insight(cat, insight)
    except Exception:
        pass


def _handle_ki_error(e):
    err = str(e)
    if "401" in err or "unauthorized" in err.lower() or "invalid_api_key" in err.lower():
        st.error("❌ API Key ungültig. Key wurde gelöscht — bitte neu eingeben.")
        set_setting('nvidia_api_key', '')
    elif "rate_limit" in err.lower() or "429" in err:
        st.error("⏱️ Zu viele Anfragen. Kurz warten und nochmal versuchen.")
    elif "402" in err or "credit" in err.lower() or "quota" in err.lower():
        st.error("💳 Kostenloses Kontingent aufgebraucht. Neue Credits unter build.nvidia.com holen.")
    else:
        st.error(f"❌ Fehler: {err}")


def ki_plan_task(api_key, task_description, task_date_str):
    """Call KI to decompose a task into subtasks. Returns list of dicts or None on error."""
    try:
        from openai import OpenAI as _OpenAI
        client = _OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)
        today = date.today().isoformat()
        categories = get_categories()
        cat_names = ", ".join(f'"{c["name"]}"' for c in categories)

        system_prompt = f"""Du bist ein ADHS-freundlicher Aufgabenplaner. Heute ist {today}.
Deine Aufgabe: Zerlege eine Aufgabe in alle notwendigen Teilschritte inkl. Vorbereitungen.
Denke an ALLES: Vorbereitung am Vorabend, Packen, Reisezeit hin und zurück, Nachbereitung.
Sei konkret und praktisch. Für Termine mit Ortsangabe: schätze Fahrzeit realistisch ein.

Verfügbare Kategorien: {cat_names}

Antworte NUR mit validem JSON, kein Text davor oder danach:
{{
  "tasks": [
    {{
      "content": "Aufgaben-Beschreibung",
      "date": "YYYY-MM-DD",
      "time_hint": "abends" | "morgens" | "mittags" | "nachmittags" | null,
      "estimate_minutes": 15,
      "category": "Kategorie-Name aus der Liste oben",
      "micro_action": "2-min Starter für diese Aufgabe",
      "note": "Kurze Erklärung warum diese Aufgabe wichtig ist"
    }}
  ],
  "summary": "Kurze Zusammenfassung des Plans"
}}"""

        user_prompt = f"Plane diese Aufgabe/diesen Termin vollständig:\n{task_description}"
        if task_date_str:
            user_prompt += f"\nDatum des Haupttermins: {task_date_str}"

        resp = client.chat.completions.create(
            model=KIMI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1500,
            stream=False
        )
        raw = resp.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        return {"error": str(e)}


def ki_analyze_full_day(api_key):
    """
    KI reads ALL today's + tomorrow's entries, breaks each task into micro-steps,
    detects appointments and creates prep tasks for the day before.
    Returns dict with per-entry analysis + prep_tasks list.
    """
    try:
        from openai import OpenAI as _OpenAI
        client = _OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)

        today      = date.today()
        tomorrow   = today + timedelta(days=1)
        categories = get_categories()
        cat_names  = ", ".join(f'"{c["name"]}"' for c in categories)

        # Gather context: today + tomorrow entries
        conn = sqlite3.connect(DB_PATH)
        today_rows = conn.execute(
            "SELECT id, entry_type, content, estimate_minutes, micro_action, category_id, deadline "
            "FROM entries WHERE entry_date=? AND done=0",
            (today.isoformat(),)
        ).fetchall()
        tomorrow_rows = conn.execute(
            "SELECT id, entry_type, content, estimate_minutes, deadline "
            "FROM entries WHERE entry_date=? AND done=0",
            (tomorrow.isoformat(),)
        ).fetchall()
        # Upcoming deadlines (next 7 days)
        deadline_rows = conn.execute(
            "SELECT content, deadline FROM entries WHERE deadline IS NOT NULL AND done=0 "
            "ORDER BY deadline LIMIT 10"
        ).fetchall()
        # Active projects
        projects = conn.execute(
            "SELECT name, description, deadline FROM projects WHERE active=1 LIMIT 5"
        ).fetchall()
        # Past performance (avg completion rate last 7 days)
        conn.close()

        task_list = "\n".join(
            f'- ID:{r[0]} [{r[1]}] "{r[2]}" (~{r[3] or "?"}min)'
            + (f' | Mikro: {r[4]}' if r[4] else '')
            for r in today_rows
        ) or "Keine Aufgaben für heute."

        tomorrow_list = "\n".join(
            f'- "{r[2]}" (~{r[3] or "?"}min)' + (f' | Deadline: {r[4]}' if r[4] else '')
            for r in tomorrow_rows
        ) or "Nichts für morgen geplant."

        deadline_list = "\n".join(
            f'- "{r[0]}" → Deadline: {r[1]}' for r in deadline_rows
        ) or "Keine anstehenden Deadlines."

        project_list = "\n".join(
            f'- {r[0]}: {r[1] or ""}' + (f' (Deadline: {r[2]})' if r[2] else '')
            for r in projects
        ) or "Keine aktiven Projekte."

        system_prompt = f"""Du bist ein intelligenter ADHS-Aufgabenplaner. Heute ist {today.isoformat()}.
Deine Aufgabe: Analysiere alle Aufgaben des Nutzers und plane sie ADHS-gerecht:
1. Zerlege jede Aufgabe in 3-6 kleine, konkrete Mikro-Schritte (je 2-10 min)
2. Erkenne Termine/Appointments und erstelle Vorbereitungsaufgaben für den Vortag
3. Schätze die reale Zeitdauer realistisch (ADHS: +30% einkalkulieren)
4. Gib einen kurzen Kontext-Hinweis warum die Aufgabe wichtig ist
Verfügbare Kategorien: {cat_names}
Antworte NUR mit validem JSON."""

        user_prompt = f"""HEUTE ({today.isoformat()}) - Meine Aufgaben:
{task_list}

MORGEN ({tomorrow.isoformat()}) - Geplant:
{tomorrow_list}

DEADLINES (nächste 7 Tage):
{deadline_list}

AKTIVE PROJEKTE:
{project_list}

Erstelle für JEDE heutige Aufgabe (anhand der ID) eine Analyse.
Erkenne auch Termine in den morgigen Aufgaben und erstelle passende Vorbereitungsaufgaben für HEUTE.

JSON-Format:
{{
  "tasks": [
    {{
      "entry_id": 123,
      "steps": ["Schritt 1 konkret", "Schritt 2 konkret", "..."],
      "real_estimate_minutes": 45,
      "context_note": "Kurze Begründung warum wichtig",
      "summary": "Ein Satz was diese Aufgabe bringt"
    }}
  ],
  "prep_tasks": [
    {{
      "content": "Vorbereitungsaufgabe",
      "date": "{today.isoformat()}",
      "for_tomorrow": "Für was diese Vorbereitung ist",
      "estimate_minutes": 10,
      "category": "Kategorie-Name",
      "micro_action": "2-min Starter"
    }}
  ],
  "day_summary": "Gesamteinschätzung des Tages in 1-2 Sätzen",
  "focus_order": [liste der entry_ids in empfohlener Reihenfolge],
  "total_estimated_minutes": 180
}}"""

        resp = client.chat.completions.create(
            model=KIMI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ],
            max_tokens=2500,
            stream=False
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        return {"error": str(e)}


def ki_evening_review(api_key):
    """Generate an evening review: what was done, upcoming, suggestions."""
    try:
        from openai import OpenAI as _OpenAI
        client = _OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)

        today = date.today()
        conn  = sqlite3.connect(DB_PATH)
        done_today = conn.execute(
            "SELECT content, elapsed_seconds, points FROM entries "
            "WHERE entry_date=? AND done=1 ORDER BY completed_at", (today.isoformat(),)
        ).fetchall()
        open_today = conn.execute(
            "SELECT content FROM entries WHERE entry_date=? AND done=0", (today.isoformat(),)
        ).fetchall()
        upcoming = conn.execute(
            "SELECT content, deadline, entry_date FROM entries "
            "WHERE done=0 AND (deadline IS NOT NULL OR entry_date > ?) "
            "ORDER BY COALESCE(deadline, entry_date) LIMIT 10",
            (today.isoformat(),)
        ).fetchall()
        # Last 7 days completion rates
        perf = conn.execute(
            "SELECT entry_date, SUM(done), COUNT(*) FROM entries "
            "WHERE entry_date >= date(?, '-7 days') GROUP BY entry_date ORDER BY entry_date",
            (today.isoformat(),)
        ).fetchall()
        conn.close()

        done_str = "\n".join(
            f'- "{r[0]}" ({int(r[1]/60) if r[1] else "?"}min, {r[2]}pts)' for r in done_today
        ) or "Nichts erledigt."
        open_str = "\n".join(f'- "{r[0]}"' for r in open_today) or "Alles erledigt! 🎉"
        upcoming_str = "\n".join(
            f'- "{r[0]}"' + (f' → {r[1] or r[2]}' if (r[1] or r[2]) else '') for r in upcoming
        ) or "Nichts anstehendes."
        perf_str = "\n".join(
            f'- {r[0]}: {r[1]}/{r[2]} erledigt ({int(r[1]/r[2]*100) if r[2] else 0}%)'
            for r in perf
        )

        resp = client.chat.completions.create(
            model=KIMI_MODEL,
            messages=[{
                "role": "system",
                "content": (
                    f"Du bist ein empathischer ADHS-Coach. Heute ist {today.isoformat()}. "
                    "Gib ein kurzes, motivierendes Abendreview auf Deutsch. "
                    "Antworte ausschließlich mit validem JSON."
                )
            }, {
                "role": "user",
                "content": f"""HEUTE ERLEDIGT:\n{done_str}\n\nNOCH OFFEN HEUTE:\n{open_str}
\nANSTEHENDE AUFGABEN/TERMINE:\n{upcoming_str}\n\nPERFORMANCE LETZTE 7 TAGE:\n{perf_str}

JSON-Format:
{{
  "headline": "Kurze Überschrift für den Tag (1 Satz)",
  "wins": ["Erfolg 1", "Erfolg 2"],
  "open_note": "Kurzer Kommentar zu nicht erledigten Aufgaben (kein Vorwurf!)",
  "upcoming_alerts": ["Wichtiger Termin: ...", "Deadline: ..."],
  "optimization_tip": "1 konkreter Verbesserungsvorschlag für morgen",
  "motivation": "1 kurzer Motivationssatz",
  "tomorrow_focus": "Die EINE wichtigste Aufgabe für morgen"
}}"""
            }],
            max_tokens=800,
            stream=False
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        return {"error": str(e)}


def ki_training_coach(api_key):
    """Echter Trainingscoach: analysiert die Calisthenics-Session-Historie und gibt Feedback/Tipps."""
    try:
        from openai import OpenAI as _OpenAI
        client = _OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)

        today = date.today()
        conn = sqlite3.connect(DB_PATH)
        sessions = conn.execute(
            "SELECT session_date, track, exercise_name, sets_completed, target_sets, "
            "best_reps, target_reps, is_hold, clean FROM cal_sessions "
            "WHERE session_date >= date(?, '-14 days') ORDER BY session_date", (today.isoformat(),)
        ).fetchall()
        conn.close()

        prog = get_cal_progress()
        streak = get_cal_streak()

        if not sessions:
            return {"error": "no_data"}

        sess_str = "\n".join(
            f'- {r[0]} [{CAL_TRACKS.get(r[1], {}).get("label", r[1])}] "{r[2]}": '
            f'{r[3]}/{r[4]} Sätze, beste Leistung {r[5]}/{r[6]}{"s" if r[7] else " Wdh"} '
            f'{"✅ sauber" if r[8] else "⚠️ nicht ganz geschafft"}'
            for r in sessions
        )
        prog_str = "\n".join(
            f'- {CAL_TRACKS[t]["label"]}: Stufe {p["level"]+1}/{len(CAL_TRACKS[t]["levels"])} '
            f'({get_cal_exercise(t, p["level"], p["bonus"])["name"]})'
            for t, p in prog.items()
        )

        resp = client.chat.completions.create(
            model=KIMI_MODEL,
            messages=[{
                "role": "system",
                "content": (
                    f"Du bist ein erfahrener Calisthenics-Trainingscoach für einen ADHS-Athleten. "
                    f"Heute ist {today.isoformat()}. Analysiere echte Trainingsdaten der letzten 14 Tage "
                    "und erkenne Muster (Konsistenz, Stagnation, Übertraining, welcher Track hinterherhinkt). "
                    "Sei konkret, kurz und motivierend, kein Geschwafel. Antworte ausschließlich mit validem JSON."
                )
            }, {
                "role": "user",
                "content": f"""AKTUELLER FORTSCHRITT JE TRACK:\n{prog_str}

STREAK: aktuell {streak['current']} Tage, längste Serie {streak['longest']} Tage, insgesamt {streak['total_sessions']} Einheiten geloggt.

TRAININGSHISTORIE (letzte 14 Tage):
{sess_str}

JSON-Format:
{{
  "headline": "Kurzer Coach-Satz zur aktuellen Lage (1 Satz)",
  "pattern_detected": "Konkret erkanntes Muster aus den Daten (z.B. welcher Track stagniert, welcher boomt)",
  "weak_track": "Track-Key (push/pull/legs/core/skill_handstand/skill_muscleup) der am meisten Aufmerksamkeit braucht, oder null",
  "strong_track": "Track-Key mit dem besten Fortschritt, oder null",
  "next_focus": "1 konkrete Handlungsempfehlung für die nächste Einheit",
  "motivation": "1 kurzer, ehrlicher Motivationssatz passend zur Datenlage"
}}"""
            }],
            max_tokens=700,
            stream=False
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        return {"error": str(e)}


def ki_sleep_coach(api_key):
    """Analysiert Schlafrythmus-Fortschritt, Routine-Adhärenz und die echten Korrelationen zur Produktivität."""
    try:
        from openai import OpenAI as _OpenAI
        client = _OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)

        today = date.today()
        target = get_sleep_target_bedtime()
        morning_streak = get_routine_streak('morning')
        evening_streak = get_routine_streak('evening')
        patterns = analyze_routine_patterns()

        conn = sqlite3.connect(DB_PATH)
        recent_sleep = conn.execute(
            "SELECT log_date, quality_pct, bedtime, wake_time FROM sleep_logs "
            "WHERE log_date >= date(?, '-14 days') ORDER BY log_date", (today.isoformat(),)
        ).fetchall()
        conn.close()

        sleep_str = "\n".join(
            f'- {r[0]}: {r[1]}% Qualität' + (f', Bettzeit {r[2]}' if r[2] else '') + (f', Aufstehen {r[3]}' if r[3] else '')
            for r in recent_sleep
        ) or "Noch keine Schlafdaten eingetragen."

        def fmt_pattern(p, unit="% Erledigungsquote"):
            if not p:
                return "noch nicht genug Daten"
            return f"{p['hi_avg']:.0f}{unit} (n={p['n_hi']}) vs. {p['lo_avg']:.0f}{unit} (n={p['n_lo']})"

        pattern_str = (
            f"Morgenroutine voll vs. nicht voll → Erledigungsquote selber Tag: {fmt_pattern(patterns['morning_completion'])}\n"
            f"Abendroutine voll vs. nicht voll → Erledigungsquote Folgetag: {fmt_pattern(patterns['evening_next_completion'])}\n"
            f"Schlafqualität ≥75% vs. <75% → Erledigungsquote selber Tag: {fmt_pattern(patterns['sleep_quality'])}\n"
        )
        ramp_status = "Ziel erreicht" if target['reached_goal'] else f"noch {target['days_to_goal']} Tage bis 00:00"

        resp = client.chat.completions.create(
            model=KIMI_MODEL,
            messages=[{
                "role": "system",
                "content": (
                    f"Du bist ein ruhiger, sachlicher Schlaf- und Routine-Coach für einen ADHS-Athleten. "
                    f"Heute ist {today.isoformat()}. Der Nutzer baut seinen Schlafrythmus schrittweise (10 Min/Tag) "
                    f"Richtung 00:00 Bettzeit und 08:00 Aufstehen um. Analysiere die echten Daten unten und gib "
                    "eine kurze, ehrliche Einschätzung — keine generischen Schlaftipps, sondern was die Daten "
                    "konkret zeigen. Antworte ausschließlich mit validem JSON."
                )
            }, {
                "role": "user",
                "content": f"""BETTZEIT-RAMPE: heutiges Ziel {target['target_time']} Uhr (Tag {target['days_elapsed']+1}, {ramp_status}).

ROUTINE-STREAKS: Morgenroutine {morning_streak['current']} Tage am Stück voll, Abendroutine {evening_streak['current']} Tage am Stück voll.

SCHLAFDATEN (letzte 14 Tage):
{sleep_str}

ECHTE MUSTER AUS DEN DATEN:
{pattern_str}

JSON-Format:
{{
  "headline": "Kurzer Coach-Satz zur aktuellen Lage (1 Satz)",
  "pattern_detected": "Was die Daten konkret zeigen, ehrlich auch wenn 'noch nicht genug Daten'",
  "biggest_lever": "Welche EINE Sache (Bettzeit, Morgenroutine, Abendroutine) hätte aktuell den größten Hebel",
  "next_step": "1 konkrete, kleine Handlungsempfehlung für heute/morgen",
  "motivation": "1 kurzer, ehrlicher Motivationssatz passend zur Datenlage"
}}"""
            }],
            max_tokens=700,
            stream=False
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        return {"error": str(e)}


def ki_haushalt_coach(api_key):
    """Empfiehlt Haushalts-Pausen-Aufgaben für heute — Deadline-bewusst, gewählt nur aus echten Kandidaten."""
    try:
        from openai import OpenAI as _OpenAI
        client = _OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)

        today = date.today()
        suggestion = suggest_household_break_tasks()
        workload = suggestion['workload']
        status = get_household_status()
        overdue = [t for t in status if t['overdue']]
        clean_score = household_clean_score()
        wohlfuehl = household_wohlfuehl_index()

        candidates_str = "\n".join(
            f"- [{t['key']}] {t['icon']} {t['label']} ({t['frequency']}, ~{t['est_minutes']} Min, "
            f"seit {t['days_since']} Tagen{' ÜBERFÄLLIG' if t['overdue'] else ''})"
            for t in suggestion['tasks']
        ) or "Keine fälligen Aufgaben innerhalb des heutigen Zeitbudgets."

        overdue_str = "\n".join(
            f"- {t['icon']} {t['label']} (seit {t['days_since']} Tagen überfällig)" for t in overdue[:5]
        ) or "Keine überfälligen Aufgaben."

        resp = client.chat.completions.create(
            model=KIMI_MODEL,
            messages=[{
                "role": "system",
                "content": (
                    f"Du bist ein pragmatischer Haushalts-Coach für einen ADHS-Athleten. Heute ist {today.isoformat()}. "
                    "Haushalt soll als kurze, erholsame Pause zwischen Deep-Work-Sessions passieren — kein "
                    "zusätzlicher Stressfaktor. Wähle ausschließlich aus der gegebenen Kandidatenliste, erfinde "
                    "keine neuen Aufgaben. Berücksichtige die heutige Deadline-Last: an vollen Tagen nur Mini-Tasks "
                    "vorschlagen. Antworte ausschließlich mit validem JSON."
                )
            }, {
                "role": "user",
                "content": f"""HEUTIGE WORKLOAD: {workload['undone_count']} offene Aufgaben, {workload['deadlines_today']} Deadlines heute, ca. {workload['total_estimate']} Min geschätzter Aufwand.
Zeitbudget für Haushalt heute: {suggestion['budget_minutes']} Minuten.

KANDIDATEN FÜR HAUSHALTS-PAUSEN HEUTE (passend zum Budget):
{candidates_str}

ÜBERFÄLLIGE AUFGABEN (zur Info, evtl. nicht alle heute machbar):
{overdue_str}

Wohnung-Sauber-Score: {clean_score}/100, Wohlfühl-Index: {wohlfuehl}/100

JSON-Format:
{{
  "headline": "Kurzer Coach-Satz zur heutigen Lage (1 Satz)",
  "recommended_keys": ["task_key1", "task_key2"],
  "reasoning": "Warum genau diese Auswahl angesichts der heutigen Workload (1-2 Sätze)",
  "skip_today": "Was bewusst NICHT heute gemacht werden sollte und warum (1 Satz, ggf. leer)",
  "motivation": "1 kurzer Motivationssatz"
}}"""
            }],
            max_tokens=600,
            stream=False
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        return {"error": str(e)}


def _build_tagesfokus_hero(done_count, total, pts_today, today_label):
    pct     = done_count / total if total > 0 else 0
    pct_int = int(pct * 100)
    R       = 90
    cx = cy = 110
    circ    = 2 * 3.14159265 * R   # 565.49
    offset  = circ * (1 - pct)

    if pct < 0.3:
        c1, c2, glow = "#ff4757", "#ff6b81", "rgba(255,71,87,0.6)"
    elif pct < 0.6:
        c1, c2, glow = "#ffa502", "#ffcc02", "rgba(255,165,2,0.6)"
    elif pct < 0.9:
        c1, c2, glow = "#2ed573", "#00d4ff", "rgba(46,213,115,0.6)"
    else:
        c1, c2, glow = "#00d4ff", "#a29bfe", "rgba(0,212,255,0.75)"

    # Tip-dot position at arc end
    import math as _m
    angle = -_m.pi / 2 + pct * 2 * _m.pi
    tip_x = cx + R * _m.cos(angle)
    tip_y = cy + R * _m.sin(angle)
    tip_visible = "visible" if pct > 0.01 else "hidden"

    sparkle_html = ""
    if pct >= 0.99:
        sparkle_html = "".join(
            f'<div class="spark" style="--dx:{dx}px;--dy:{dy}px;--d:{d}s"></div>'
            for dx, dy, d in [(-60,-40,.0),( 60,-40,.2),(-80, 10,.4),
                               ( 80, 10,.6),(-40, 60,.8),( 40, 60,1.0)]
        )

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{background:#0e1117;font-family:-apple-system,'Segoe UI',sans-serif;overflow:hidden;height:100%}}
.hero{{display:flex;align-items:center;justify-content:center;gap:52px;height:100%;padding:0 32px}}

/* Ring */
.rw{{position:relative;width:220px;height:220px;flex-shrink:0}}
svg{{width:220px;height:220px;overflow:visible}}
.track{{fill:none;stroke:rgba(255,255,255,0.05);stroke-width:16}}
.arc{{fill:none;stroke:url(#g);stroke-width:16;stroke-linecap:round;
  stroke-dasharray:{circ:.2f};stroke-dashoffset:{circ:.2f};
  filter:drop-shadow(0 0 10px {glow});
  animation:fill-in 1.5s cubic-bezier(.22,1,.36,1) forwards,
             breathe 3s ease-in-out 1.5s infinite}}
@keyframes fill-in{{to{{stroke-dashoffset:{offset:.2f}}}}}
@keyframes breathe{{
  0%,100%{{filter:drop-shadow(0 0 8px {glow})}}
  50%{{filter:drop-shadow(0 0 20px {glow}) drop-shadow(0 0 40px {c1}44)}}}}

/* Tip glow dot */
.tip{{position:absolute;width:14px;height:14px;border-radius:50%;
  background:{c1};visibility:{tip_visible};
  box-shadow:0 0 0 3px #0e1117,0 0 14px {c1},0 0 28px {c1}88;
  transform:translate(-50%,-50%);
  left:{tip_x/220*100:.2f}%;top:{tip_y/220*100:.2f}%;
  animation:tip-pulse 1.8s ease-in-out infinite}}
@keyframes tip-pulse{{0%,100%{{box-shadow:0 0 0 3px #0e1117,0 0 12px {c1},0 0 24px {c1}66}}
  50%{{box-shadow:0 0 0 3px #0e1117,0 0 20px {c1},0 0 40px {c1}}}}}

/* Center text */
.ct{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center}}
.pct{{font-size:50px;font-weight:900;letter-spacing:-3px;line-height:1;
  background:linear-gradient(145deg,{c1},{c2});
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.sub{{font-size:10px;font-weight:700;letter-spacing:3px;color:rgba(255,255,255,.25);margin-top:2px}}

/* Stats */
.stats{{display:flex;flex-direction:column;gap:14px}}
.card{{position:relative;background:rgba(255,255,255,.03);
  border:1px solid rgba(255,255,255,.07);
  border-left:3px solid {c1};
  border-radius:14px;padding:14px 28px;min-width:160px;overflow:hidden}}
.card::before{{content:'';position:absolute;inset:0;
  background:linear-gradient(135deg,{c1}08,transparent 60%);pointer-events:none}}
.cv{{font-size:36px;font-weight:900;line-height:1;
  background:linear-gradient(135deg,{c1},{c2});
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.ck{{font-size:9px;font-weight:700;letter-spacing:2px;color:rgba(255,255,255,.3);margin-top:4px}}

/* Sparkles at 100% */
.spark{{position:absolute;width:6px;height:6px;border-radius:50%;
  background:{c1};box-shadow:0 0 8px {c1};
  top:50%;left:50%;
  animation:spark-out 1.6s ease-out var(--d) infinite}}
@keyframes spark-out{{
  0%{{transform:translate(0,0) scale(1);opacity:1}}
  100%{{transform:translate(var(--dx),var(--dy)) scale(0);opacity:0}}}}
</style></head><body>
<div class="hero">
  <div class="rw">
    <svg viewBox="0 0 220 220">
      <defs>
        <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="{c1}"/>
          <stop offset="100%" stop-color="{c2}"/>
        </linearGradient>
      </defs>
      <circle class="track" cx="{cx}" cy="{cy}" r="{R}" transform="rotate(-90,{cx},{cy})"/>
      <circle class="arc"   cx="{cx}" cy="{cy}" r="{R}" transform="rotate(-90,{cx},{cy})"/>
    </svg>
    <div class="tip"></div>
    <div class="ct">
      <div class="pct">{pct_int}%</div>
      <div class="sub">ERLEDIGT</div>
    </div>
    {sparkle_html}
  </div>
  <div class="stats">
    <div class="card">
      <div class="cv">{done_count}<span style="font-size:20px;opacity:.4">/{total}</span></div>
      <div class="ck">AUFGABEN</div>
    </div>
    <div class="card">
      <div class="cv">{pts_today}</div>
      <div class="ck">PUNKTE HEUTE</div>
    </div>
  </div>
</div>
</body></html>"""


def render_ki_planner_section(api_key):
    """Renders the KI task planner inside the Planen page."""
    st.markdown("### 🤖 KI-Aufgabenplaner")
    st.caption("Beschreibe einen Termin oder eine komplexe Aufgabe — KI plant alles automatisch: Vorbereitung, Reisezeit, Nachbereitung.")

    with st.form("ki_planner_form"):
        task_input = st.text_area(
            "Termin / Aufgabe beschreiben",
            placeholder='z.B. "Psychologen Termin morgen 14:00 Uhr, Praxis in der Innenstadt, ~20 min Fahrzeit"\noder "Präsentation am Freitag um 10:00 Uhr vorbereiten"',
            height=100
        )
        col_date, col_hint = st.columns([1, 1])
        with col_date:
            task_date = st.date_input("Datum des Haupttermins", value=date.today() + timedelta(days=1))
        with col_hint:
            st.write("")
            st.write("")
            st.caption("KI plant auch Vorbereitungen für die Vortage.")
        submitted = st.form_submit_button("🤖 Plan erstellen", use_container_width=True)

    if submitted and task_input.strip():
        with st.spinner("KI plant deinen Termin..."):
            result = ki_plan_task(api_key, task_input.strip(), task_date.isoformat())

        if "error" in result:
            st.error(f"Fehler: {result['error']}")
            return

        st.session_state['ki_plan_result'] = result
        st.session_state['ki_plan_checked'] = {i: True for i in range(len(result.get('tasks', [])))}

    if 'ki_plan_result' in st.session_state:
        result = st.session_state['ki_plan_result']
        tasks = result.get('tasks', [])
        summary = result.get('summary', '')

        if summary:
            st.info(f"📋 {summary}")

        if not tasks:
            st.warning("KI hat keine Aufgaben generiert.")
            return

        categories = get_categories()
        cat_names  = [c['name'] for c in categories]

        st.markdown(f"**{len(tasks)} Aufgaben geplant** — wähle welche du hinzufügen möchtest:")

        for i, t in enumerate(tasks):
            checked = st.session_state['ki_plan_checked'].get(i, True)
            col_chk, col_content = st.columns([0.05, 0.95])
            with col_chk:
                new_checked = st.checkbox("", value=checked, key=f"ki_task_chk_{i}",
                                          label_visibility="collapsed")
                st.session_state['ki_plan_checked'][i] = new_checked
            with col_content:
                date_str  = t.get('date', date.today().isoformat())
                time_hint = t.get('time_hint', '')
                est       = t.get('estimate_minutes', 0)
                cat_name  = t.get('category', '')
                cat_obj   = next((c for c in categories if c['name'] == cat_name), None)
                cat_badge = (f'<span style="background:{cat_obj["color"]}28;color:{cat_obj["color"]};'
                             f'font-size:10px;font-weight:700;padding:1px 7px;border-radius:8px;'
                             f'border:1px solid {cat_obj["color"]}44">{cat_obj["icon"]} {cat_name}</span>'
                             if cat_obj else '')
                micro = t.get('micro_action', '')
                note  = t.get('note', '')
                time_label = f" · {time_hint}" if time_hint else ""
                st.markdown(
                    f'<div style="padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.06);'
                    f'opacity:{"1" if new_checked else "0.35"}">'
                    f'<strong>{t["content"]}</strong> {cat_badge}<br>'
                    f'<span style="font-size:11px;color:rgba(255,255,255,0.4)">'
                    f'📅 {date_str}{time_label} · ⏱️ ~{est} min'
                    f'{"  ·  ⚡ " + micro if micro else ""}</span>'
                    f'{"<br><span style=\'font-size:10px;color:rgba(255,255,255,0.3)\'>" + note + "</span>" if note else ""}'
                    f'</div>',
                    unsafe_allow_html=True
                )

        st.write("")
        selected_count = sum(1 for v in st.session_state['ki_plan_checked'].values() if v)
        col_add, col_clear = st.columns([2, 1])
        with col_add:
            if st.button(f"✅ {selected_count} Aufgaben hinzufügen", key="ki_plan_add",
                         use_container_width=True, disabled=selected_count == 0):
                added = 0
                for i, t in enumerate(tasks):
                    if not st.session_state['ki_plan_checked'].get(i):
                        continue
                    cat_name = t.get('category', '')
                    cat_obj  = next((c for c in categories if c['name'] == cat_name), None)
                    new_id = add_entry(
                        "brain",
                        t['content'],
                        estimate=t.get('estimate_minutes', 0),
                        entry_date=t.get('date', date.today().isoformat())
                    )
                    if new_id:
                        if cat_obj:
                            set_entry_category(new_id, cat_obj['id'])
                        micro = t.get('micro_action', '').strip()
                        if micro:
                            conn_kp = sqlite3.connect(DB_PATH)
                            conn_kp.execute("UPDATE entries SET micro_action=? WHERE id=?", (micro, new_id))
                            conn_kp.commit()
                            conn_kp.close()
                    added += 1
                del st.session_state['ki_plan_result']
                del st.session_state['ki_plan_checked']
                st.success(f"✅ {added} Aufgaben wurden hinzugefügt!")
                st.rerun()
        with col_clear:
            if st.button("✕ Verwerfen", key="ki_plan_clear", use_container_width=True):
                del st.session_state['ki_plan_result']
                del st.session_state['ki_plan_checked']
                st.rerun()


def render_ki_coach_page():
    st.title("🤖 KI Coach")

    try:
        from openai import OpenAI as _OpenAI
    except ImportError:
        st.error("Das `openai` Paket ist nicht installiert.")
        st.code("pip install openai", language="bash")
        return

    api_key = get_setting('nvidia_api_key', '')

    if not api_key:
        st.info(
            "**Kostenlos starten:** [build.nvidia.com/moonshotai/kimi-k2.6](https://build.nvidia.com/moonshotai/kimi-k2.6) "
            "→ **Get API Key** → Key eintragen. Gratis Credits beim ersten Anmelden."
        )
        with st.form("api_key_form"):
            new_key = st.text_input("NVIDIA API Key", type="password", placeholder="nvapi-...")
            if st.form_submit_button("Aktivieren", use_container_width=True):
                if new_key.strip():
                    set_setting('nvidia_api_key', new_key.strip())
                    st.rerun()
        return

    client = _OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)

    with st.expander("⚙️ API Key & Muster", expanded=False):
        masked = api_key[:10] + "..." + api_key[-4:] if len(api_key) > 14 else "***"
        insights_count = len(get_ki_insights())
        st.caption(f"Key: `{masked}` ✅  |  Kimi K2.6  |  {insights_count} gelernte Muster")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Key löschen", key="ki_del_key"):
                set_setting('nvidia_api_key', '')
                for k in ['ki_chat_history']:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()
        with c2:
            if insights_count and st.button("Muster anzeigen", key="ki_show_ins"):
                st.session_state.ki_show_insights = not st.session_state.get('ki_show_insights', False)
        if st.session_state.get('ki_show_insights'):
            for cat, ins, _ in get_ki_insights():
                st.markdown(f"- **[{cat}]** {ins}")

    base_system = """Du bist ein persönlicher ADHS-Coach für die Kaizen Produktivitäts-App. Du lernst kontinuierlich aus den Daten des Nutzers und wirst über die Zeit immer besser.

Grundregeln:
- Antworte immer auf Deutsch
- Sei direkt, ehrlich, motivierend — kein Bullshit, keine leeren Phrasen
- ADHS-freundlich: eine Sache nach der anderen, keine überladenen Listen
- Nutze die echten Daten für konkrete, personalisierte Aussagen
- Emojis sparsam aber gezielt"""

    tab_chat, tab_daily, tab_weekly, tab_journal = st.tabs([
        "💬 Chat", "📊 KI Daily Review", "📅 KI Weekly Review", "📔 Mein Tagebuch"
    ])

    with tab_chat:
        _render_ki_chat_tab(client, base_system)
    with tab_daily:
        _render_ki_review_tab(client, "ki_daily", days_back=0, base_system=base_system)
    with tab_weekly:
        _render_ki_review_tab(client, "ki_weekly", days_back=6, base_system=base_system)
    with tab_journal:
        _render_user_journal_tab()


def _render_ki_chat_tab(client, base_system):
    st.caption("Frag deinen Coach — er kennt alle deine Daten und lernt dich über die Zeit besser kennen.")

    if 'ki_chat_history' not in st.session_state:
        st.session_state.ki_chat_history = []

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📋 Tages-Briefing", use_container_width=True, key="ki_briefing"):
            st.session_state.ki_pending = "Gib mir ein kurzes Tages-Briefing. Was ist heute wichtig? Was ist überfällig? Wo stehe ich?"
    with col2:
        if st.button("🎯 Was jetzt?", use_container_width=True, key="ki_now"):
            st.session_state.ki_pending = "Was soll ich jetzt tun? Nenn mir NUR eine Aufgabe mit kurzer Begründung."
    with col3:
        if st.button("⚠️ Deadline-Check", use_container_width=True, key="ki_deadlines"):
            st.session_state.ki_pending = "Analysiere meine Deadlines und Projekte. Was ist kritisch? Was muss heute noch erledigt werden?"
    with col4:
        if st.button("🗑️ Chat leeren", use_container_width=True, key="ki_clear"):
            st.session_state.ki_chat_history = []
            st.rerun()

    st.markdown("---")

    for msg in st.session_state.ki_chat_history:
        with st.chat_message(msg['role']):
            st.markdown(msg['content'])

    pending = None
    if 'ki_pending' in st.session_state:
        pending = st.session_state['ki_pending']
        del st.session_state['ki_pending']

    user_input = st.chat_input("Frag deinen KI Coach...")
    final_input = pending or user_input
    if not final_input:
        return

    with st.chat_message('user'):
        st.markdown(final_input)

    context = build_ai_context(days_back=0)
    system = base_system + f"\n\n**Aktuelle Nutzerdaten:**\n{context}"
    messages = [{"role": "system", "content": system}]
    for m in st.session_state.ki_chat_history:
        messages.append({"role": m['role'], "content": m['content']})
    messages.append({"role": "user", "content": final_input})

    try:
        with st.chat_message('assistant'):
            placeholder = st.empty()
            full_text = _ki_stream(client, messages, placeholder, max_tokens=512)
        st.session_state.ki_chat_history.append({'role': 'user', 'content': final_input})
        st.session_state.ki_chat_history.append({'role': 'assistant', 'content': full_text})
    except Exception as e:
        _handle_ki_error(e)


def _render_ki_review_tab(client, review_type, days_back, base_system):
    is_weekly = (review_type == "ki_weekly")
    label = "Wochen" if is_weekly else "Tages"
    today_str = date.today().isoformat()
    review_date_key = (date.today() - timedelta(days=days_back)).isoformat() if is_weekly else today_str

    st.caption(
        f"Vollständige KI-Analyse {'der letzten 7 Tage' if is_weekly else 'von heute'} — "
        "alle Stats, Muster, Bewertung, Empfehlungen. Die KI lernt mit jedem Review mehr über dich."
    )

    latest = get_reviews(review_type, limit=1)
    col_gen, col_info = st.columns([1, 2])
    with col_gen:
        generate = st.button(f"🔄 {label}-Review generieren", use_container_width=True, key=f"gen_{review_type}")
    with col_info:
        if latest:
            st.caption(f"Letzter Review: {latest[0][2]} (erstellt {latest[0][3][:10]})")
        else:
            st.caption("Noch kein Review vorhanden.")

    if generate:
        context = build_ai_context(days_back=days_back)

        if is_weekly:
            prompt = f"""Erstelle einen vollständigen WOCHEN-REVIEW. Nutze ausschließlich die echten Daten.

## 📊 Wochenstatistiken
[Zahlen & Fakten: Tasks erledigt/offen, Zeit investiert, Punkte, Level, Projektfortschritt]

## 🏆 Was diese Woche gut lief
[Konkrete Erfolge mit echten Task-Namen, positive Muster]

## ⚠️ Herausforderungen & Misses
[Was nicht geklappt hat, überfällige Aufgaben — ehrlich aber konstruktiv]

## 📈 Trends & Muster
[Beste/schlechteste Tage, Aufgabentyp-Präferenzen, Deadline-Verhalten, Energiemuster]

## 🎯 Projekte-Status
[Fortschritt bei jedem aktiven Projekt, Risiken, Priorisierung]

## 💡 Was ich über dich gelernt habe
[2-3 neue oder bestätigte Erkenntnisse über Arbeitsweise, Stärken, Herausforderungen]

## 🚀 Empfehlungen für nächste Woche
[Maximal 3 konkrete, umsetzbare Maßnahmen — priorisiert]

## 💪 Gesamtbewertung
[Ehrliche Einschätzung mit Motivationsboost, 2-3 Sätze]

Daten:
{context}"""
        else:
            prompt = f"""Erstelle einen vollständigen TAGES-REVIEW. Nutze ausschließlich die echten Daten.

## 📊 Zahlen des Tages
[Tasks erledigt/offen, Zeit investiert, Punkte verdient, Level-Stand, Routinen erledigt]

## ✅ Was heute gut lief
[Konkrete Erfolge mit echten Task-Namen, positive Muster des Tages]

## 🔴 Was nicht geschafft wurde
[Offene Tasks, Überfälligkeiten — ehrlich, nicht vernichtend, lösungsorientiert]

## 🔍 Analyse & Muster
[Warum hat es gut/schlecht geklappt? Aufgabentyp-Insights? Energiemuster?]

## 🎯 Projekte & Deadlines
[Status aktiver Projekte, kritische Fristen, nächste Schritte]

## 🚀 Empfehlungen für morgen
[Maximal 3 konkrete Aktionen, priorisiert nach Wichtigkeit]

## 💪 Gesamtbewertung des Tages
[Motivierende, ehrliche Einschätzung — 2-3 Sätze]

Daten:
{context}"""

        messages = [
            {"role": "system", "content": base_system + "\nDu erstellst einen detaillierten Produktivitäts-Review. Sei ausführlich, konkret, nutze alle Daten."},
            {"role": "user", "content": prompt}
        ]

        try:
            with st.container():
                placeholder = st.empty()
                full_text = _ki_stream(client, messages, placeholder, max_tokens=1500)
            save_review(review_type, full_text, review_date_key)
            _extract_and_save_insights(client, full_text)
            st.success(f"✅ {label}-Review gespeichert — neue Muster gelernt!")
            st.rerun()
        except Exception as e:
            _handle_ki_error(e)
        return

    if latest:
        rev_id, content, rev_date, created_at = latest[0]
        st.markdown(f"*Review vom {rev_date} — erstellt {created_at[:10]}*")
        st.markdown("---")
        st.markdown(content)
        all_reviews = get_reviews(review_type, limit=10)
        if len(all_reviews) > 1:
            with st.expander(f"📁 Ältere {label}-Reviews ({len(all_reviews) - 1} weitere)"):
                for rev in all_reviews[1:]:
                    with st.expander(f"{rev[2]} — {rev[3][:10]}"):
                        st.markdown(rev[1])
    else:
        st.info(f"Noch kein {label}-Review vorhanden. Klick auf **{label}-Review generieren** um zu starten.")


def _render_user_journal_tab():
    st.caption("Dein persönlicher Raum — Brain Dumps, Reflexionen, was dich wirklich bewegt.")

    subtab_daily, subtab_weekly, subtab_history = st.tabs(["📝 Heute", "📅 Diese Woche", "📁 Verlauf"])

    with subtab_daily:
        st.subheader(f"Tages-Reflexion — {date.today().strftime('%d.%m.%Y')}")
        today_journal = get_reviews('user_daily', limit=1)
        today_exists = today_journal and today_journal[0][2] == date.today().isoformat()

        if today_exists and not st.session_state.get('journal_edit_daily'):
            st.success("✅ Heute bereits geschrieben.")
            st.markdown(today_journal[0][1])
            if st.button("✏️ Überschreiben", key="journal_overwrite_daily"):
                st.session_state.journal_edit_daily = True
                st.rerun()
        else:
            with st.form("user_daily_journal"):
                mood = st.select_slider("Wie war dein Tag?",
                    options=["😫 Sehr schlecht", "😕 Schlecht", "😐 Okay", "🙂 Gut", "😊 Super"],
                    value="😐 Okay")
                happened = st.text_area("Brain Dump — Alles raus:", height=120,
                                         placeholder="Was hat dich heute beschäftigt? Gedanken, Gefühle, Erlebnisse — ohne Filter")
                went_well = st.text_area("Was lief gut?", height=80,
                                          placeholder="Auch kleine Dinge zählen...")
                was_hard = st.text_area("Was war schwierig?", height=80,
                                         placeholder="Ehrlich reflektieren, ohne Selbstkritik")
                tomorrow = st.text_area("Intention für morgen:", height=60,
                                         placeholder="Eine Sache, die morgen wirklich wichtig ist...")
                if st.form_submit_button("💾 Speichern", use_container_width=True):
                    content = f"**Stimmung:** {mood}\n\n"
                    if happened.strip():
                        content += f"**Brain Dump:**\n{happened}\n\n"
                    if went_well.strip():
                        content += f"**Was gut lief:**\n{went_well}\n\n"
                    if was_hard.strip():
                        content += f"**Was schwierig war:**\n{was_hard}\n\n"
                    if tomorrow.strip():
                        content += f"**Intention für morgen:**\n{tomorrow}"
                    save_review('user_daily', content.strip(), date.today().isoformat())
                    if 'journal_edit_daily' in st.session_state:
                        del st.session_state['journal_edit_daily']
                    st.rerun()

    with subtab_weekly:
        week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
        st.subheader(f"Wochen-Reflexion — KW ab {week_start}")
        week_journal = get_reviews('user_weekly', limit=1)
        week_exists = week_journal and week_journal[0][2] == week_start

        if week_exists and not st.session_state.get('journal_edit_weekly'):
            st.success("✅ Diese Woche bereits geschrieben.")
            st.markdown(week_journal[0][1])
            if st.button("✏️ Überschreiben", key="journal_overwrite_weekly"):
                st.session_state.journal_edit_weekly = True
                st.rerun()
        else:
            with st.form("user_weekly_journal"):
                mood_week = st.select_slider("Wie war deine Woche?",
                    options=["😫 Sehr schlecht", "😕 Schlecht", "😐 Okay", "🙂 Gut", "😊 Super"],
                    value="😐 Okay")
                week_dump = st.text_area("Wochen-Braindump:", height=150,
                                          placeholder="Alles raus: Projekte, Gedanken, Gefühle, Beobachtungen der Woche...")
                week_wins = st.text_area("Top Wins der Woche:", height=80,
                                          placeholder="Was hast du diese Woche wirklich erreicht?")
                week_learn = st.text_area("Was habe ich über mich gelernt?", height=80,
                                           placeholder="Erkenntnisse, Muster, Überraschungen...")
                next_week_goal = st.text_area("Fokus für nächste Woche:", height=60,
                                               placeholder="Ein großes Ziel oder Thema für die kommende Woche...")
                if st.form_submit_button("💾 Speichern", use_container_width=True):
                    content = f"**Stimmung:** {mood_week}\n\n"
                    if week_dump.strip():
                        content += f"**Wochen-Braindump:**\n{week_dump}\n\n"
                    if week_wins.strip():
                        content += f"**Top Wins:**\n{week_wins}\n\n"
                    if week_learn.strip():
                        content += f"**Erkenntnisse:**\n{week_learn}\n\n"
                    if next_week_goal.strip():
                        content += f"**Fokus nächste Woche:**\n{next_week_goal}"
                    save_review('user_weekly', content.strip(), week_start)
                    if 'journal_edit_weekly' in st.session_state:
                        del st.session_state['journal_edit_weekly']
                    st.rerun()

    with subtab_history:
        st.subheader("Verlauf")
        hist_type = st.selectbox("Typ", ["Tages-Reflexionen", "Wochen-Reflexionen"], key="journal_hist_type")
        rtype = "user_daily" if hist_type == "Tages-Reflexionen" else "user_weekly"
        past = get_reviews(rtype, limit=20)
        if not past:
            st.info("Noch keine Einträge vorhanden.")
        else:
            for rev in past:
                with st.expander(f"📅 {rev[2]} — {rev[3][:10]}"):
                    st.markdown(rev[1])


# ========== SHARED CSS ==========

URGENCY_CSS = """<style>
@keyframes glow-red {
    0%,100% { box-shadow: 0 0 6px rgba(239,68,68,0.4); }
    50%      { box-shadow: 0 0 22px rgba(239,68,68,0.85); }
}
@keyframes glow-orange {
    0%,100% { box-shadow: 0 0 4px rgba(249,115,22,0.3); }
    50%      { box-shadow: 0 0 16px rgba(249,115,22,0.7); }
}
.urg-overdue  { border-left:5px solid #ef4444; background:rgba(239,68,68,0.09);
                border-radius:10px; padding:14px 18px; margin-bottom:10px;
                animation: glow-red 1.8s ease-in-out infinite; }
.urg-today    { border-left:5px solid #f97316; background:rgba(249,115,22,0.08);
                border-radius:10px; padding:14px 18px; margin-bottom:10px;
                animation: glow-orange 2.5s ease-in-out infinite; }
.urg-tomorrow { border-left:4px solid #eab308; background:rgba(234,179,8,0.07);
                border-radius:8px; padding:12px 16px; margin-bottom:8px; }
.urg-soon     { border-left:4px solid #84cc16; background:rgba(132,204,22,0.06);
                border-radius:8px; padding:12px 16px; margin-bottom:8px; }
.urg-later    { border-left:3px solid #60a5fa; background:rgba(96,165,250,0.05);
                border-radius:8px; padding:12px 16px; margin-bottom:8px; }
.urg-none     { border-left:3px solid #475569; background:rgba(71,85,105,0.04);
                border-radius:8px; padding:12px 16px; margin-bottom:8px; }
.urg-done     { opacity:0.32; text-decoration:line-through; }
.dl-badge     { display:inline-block; font-size:12px; font-weight:600;
                padding:2px 8px; border-radius:20px; margin-left:8px;
                background:rgba(255,255,255,0.08); }
/* Fokus page cards */
.fok-hl  { border-left:5px solid #ffd700; background:rgba(255,215,0,0.07);
           border-radius:10px; padding:14px 18px; margin-bottom:12px; }
.fok-mc  { border-left:4px solid #4ade80; background:rgba(74,222,128,0.06);
           border-radius:8px; padding:10px 15px; margin-bottom:8px; }
.fok-br  { border-left:4px solid #60a5fa; background:rgba(96,165,250,0.06);
           border-radius:8px; padding:10px 15px; margin-bottom:8px; }
.fok-done { opacity:0.35; text-decoration:line-through; }
</style>"""


# ========== PAGES ==========

def render_lofi_start_page():
    import requests as _req

    stats = get_analytics_stats()
    today = date.today()

    # ── Static files ──────────────────────────────────────────
    try:
        with open('static/styles.css', 'r', encoding='utf-8') as f:
            css = f.read()
    except Exception:
        css = ''
    try:
        with open('static/rain.js', 'r', encoding='utf-8') as f:
            js = f.read()
    except Exception:
        js = ''

    # ── DB stats ──────────────────────────────────────────────
    conn = sqlite3.connect(DB_PATH)
    done_today  = conn.execute("SELECT COUNT(*) FROM entries WHERE entry_date=? AND done=1",   (today.isoformat(),)).fetchone()[0]
    total_today = conn.execute("SELECT COUNT(*) FROM entries WHERE entry_date=?",               (today.isoformat(),)).fetchone()[0]
    pts_today   = conn.execute("SELECT COALESCE(SUM(points),0) FROM entries WHERE entry_date=? AND done=1", (today.isoformat(),)).fetchone()[0] or 0
    deadline_alerts = conn.execute(
        "SELECT content, deadline FROM entries WHERE done=0 AND deadline IS NOT NULL "
        "AND deadline != '' AND deadline <= date(?, '+7 days') ORDER BY deadline LIMIT 5",
        (today.isoformat(),)
    ).fetchall()
    conn.close()

    pct_today = int(done_today / total_today * 100) if total_today > 0 else 0

    # ── Weather (wttr.in, no API key) ─────────────────────────
    weather_html = ""
    try:
        wr = _req.get("https://wttr.in/?format=j1", timeout=3)
        if wr.status_code == 200:
            wd = wr.json()
            cur = wd['current_condition'][0]
            temp_c   = cur['temp_C']
            feels_c  = cur['FeelsLikeC']
            desc     = cur['weatherDesc'][0]['value']
            humidity = cur['humidity']
            wcode    = int(cur['weatherCode'])
            if   wcode == 113:                        wemoji = "☀️"
            elif wcode == 116:                        wemoji = "⛅"
            elif wcode in [119, 122]:                 wemoji = "☁️"
            elif wcode in [143, 248, 260]:            wemoji = "🌫️"
            elif wcode in [200, 386, 389, 392, 395]:  wemoji = "⛈️"
            elif wcode in [227, 230]:                 wemoji = "❄️"
            elif wcode in [176, 179, 182, 185, 263, 266, 281, 284,
                           293, 296, 299, 302, 305, 308]: wemoji = "🌧️"
            elif wcode in [311, 314, 317, 320, 323, 326, 329, 332,
                           335, 338, 350, 353, 356, 359, 362, 365,
                           368, 371, 374, 377]:       wemoji = "🌨️"
            else:                                     wemoji = "🌡️"
            weather_html = f"""
<div style="background:rgba(255,255,255,0.05);border-radius:14px;padding:16px;
            border:1px solid rgba(255,255,255,0.08);height:100%">
  <div style="font-size:9px;color:rgba(255,255,255,0.35);letter-spacing:2px;
              text-transform:uppercase;margin-bottom:10px">🌍 Wetter</div>
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px">
    <div style="font-size:42px;line-height:1">{wemoji}</div>
    <div>
      <div style="font-size:30px;font-weight:900;color:white;line-height:1">{temp_c}°C</div>
      <div style="font-size:11px;color:rgba(255,255,255,0.45);margin-top:2px">
        Gefühlt {feels_c}°</div>
    </div>
  </div>
  <div style="font-size:12px;color:rgba(255,255,255,0.7);margin-bottom:6px">{desc}</div>
  <div style="font-size:10px;color:rgba(255,255,255,0.35)">💧 {humidity}% Luftfeuchtigkeit</div>
</div>"""
    except Exception:
        weather_html = """
<div style="background:rgba(255,255,255,0.05);border-radius:14px;padding:16px;
            border:1px solid rgba(255,255,255,0.08)">
  <div style="font-size:9px;color:rgba(255,255,255,0.35);letter-spacing:2px;
              text-transform:uppercase;margin-bottom:10px">🌍 Wetter</div>
  <div style="font-size:32px;margin-bottom:6px">🌐</div>
  <div style="font-size:12px;color:rgba(255,255,255,0.3)">Nicht verfügbar</div>
</div>"""

    # ── Stats card ────────────────────────────────────────────
    bar_col = "#e74c3c" if pct_today < 30 else "#f39c12" if pct_today < 65 else "#2ecc71"
    stats_html = f"""
<div style="background:rgba(255,255,255,0.05);border-radius:14px;padding:16px;
            border:1px solid rgba(255,255,255,0.08)">
  <div style="font-size:9px;color:rgba(255,255,255,0.35);letter-spacing:2px;
              text-transform:uppercase;margin-bottom:12px">
    📊 Heute · {today.strftime('%d.%m.%Y')}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:14px">
    <div style="text-align:center;background:rgba(0,212,255,0.08);border-radius:10px;padding:10px 4px">
      <div style="font-size:24px;font-weight:900;color:#00d4ff">{done_today}</div>
      <div style="font-size:9px;color:rgba(255,255,255,0.45);margin-top:2px">Erledigt</div>
    </div>
    <div style="text-align:center;background:rgba(255,215,0,0.08);border-radius:10px;padding:10px 4px">
      <div style="font-size:24px;font-weight:900;color:#ffd700">{pts_today}</div>
      <div style="font-size:9px;color:rgba(255,255,255,0.45);margin-top:2px">Punkte</div>
    </div>
    <div style="text-align:center;background:rgba(162,155,254,0.1);border-radius:10px;padding:10px 4px">
      <div style="font-size:24px;font-weight:900;color:#a29bfe">{total_today - done_today}</div>
      <div style="font-size:9px;color:rgba(255,255,255,0.45);margin-top:2px">Offen</div>
    </div>
  </div>
  <div style="font-size:9px;color:rgba(255,255,255,0.35);margin-bottom:5px">
    Fortschritt {pct_today}%</div>
  <div style="background:rgba(255,255,255,0.1);border-radius:4px;height:5px;overflow:hidden">
    <div style="width:{pct_today}%;height:100%;background:{bar_col};border-radius:4px"></div>
  </div>
  <div style="margin-top:10px;display:flex;justify-content:space-between;
              font-size:9px;color:rgba(255,255,255,0.25)">
    <span>🏆 {stats['completed']} Aufgaben total</span>
    <span>⏱️ {stats['total_minutes']} Min</span>
  </div>
</div>"""

    # ── Deadlines card ────────────────────────────────────────
    dl_items = ""
    for content, dl in deadline_alerts:
        if not dl or not dl.strip():
            continue
        try:
            days_left = (date.fromisoformat(dl.strip()) - today).days
        except ValueError:
            continue
        d_col   = "#e74c3c" if days_left <= 1 else "#f39c12" if days_left <= 3 else "#00d4ff"
        d_label = "Heute!" if days_left == 0 else "Morgen" if days_left == 1 else f"in {days_left}d"
        dl_items += f"""
<div style="padding:7px 10px;margin:4px 0;background:rgba(255,255,255,0.04);
            border-left:3px solid {d_col};border-radius:0 8px 8px 0">
  <div style="font-size:12px;color:white;white-space:nowrap;overflow:hidden;
              text-overflow:ellipsis">{content}</div>
  <div style="font-size:10px;color:{d_col};margin-top:2px">⏰ {dl} · {d_label}</div>
</div>"""

    if dl_items:
        deadlines_html = f"""
<div style="background:rgba(255,255,255,0.05);border-radius:14px;padding:16px;
            border:1px solid rgba(255,255,255,0.08)">
  <div style="font-size:9px;color:rgba(255,255,255,0.35);letter-spacing:2px;
              text-transform:uppercase;margin-bottom:10px">⚠️ Anstehende Deadlines</div>
  {dl_items}
</div>"""
    else:
        deadlines_html = """
<div style="background:rgba(255,255,255,0.05);border-radius:14px;padding:16px;
            border:1px solid rgba(255,255,255,0.08)">
  <div style="font-size:9px;color:rgba(255,255,255,0.35);letter-spacing:2px;
              text-transform:uppercase;margin-bottom:10px">⚠️ Deadlines</div>
  <div style="font-size:12px;color:rgba(255,255,255,0.25);text-align:center;padding:20px 0">
    ✅ Keine Deadlines in den<br>nächsten 7 Tagen</div>
</div>"""

    # ── Hero Canvas ───────────────────────────────────────────
    html_hero = f"""<!DOCTYPE html>
<html><head><style>
  html,body{{margin:0;padding:0;height:100%;background:#0e1117;overflow:hidden}}
  canvas{{position:absolute;inset:0;width:100%;height:100%}}
  .overlay{{position:absolute;inset:0;display:flex;flex-direction:column;
             align-items:center;justify-content:center;pointer-events:none;
             font-family:system-ui,-apple-system,sans-serif}}
  .greeting{{font-size:12px;letter-spacing:4px;text-transform:uppercase;
              color:rgba(255,255,255,0.35);margin-bottom:10px}}
  .clock{{font-size:58px;font-weight:900;color:white;letter-spacing:2px;line-height:1;
           text-shadow:0 0 40px rgba(0,212,255,0.6);margin-bottom:8px}}
  .datestr{{font-size:14px;color:rgba(255,255,255,0.45);letter-spacing:1px}}
  .tagline{{margin-top:18px;font-size:12px;
             background:linear-gradient(90deg,#00d4ff,#a29bfe);
             -webkit-background-clip:text;-webkit-text-fill-color:transparent;
             letter-spacing:1px}}
  {css}
</style></head><body>
<canvas id="rain" width="1200" height="340"></canvas>
<div class="overlay">
  <div class="greeting" id="greeting">–</div>
  <div class="clock"    id="clock">00:00</div>
  <div class="datestr"  id="datestr">–</div>
  <div class="tagline">Eins nach dem anderen · jeden Tag ein bisschen besser</div>
</div>
<script>
{js}
var DAYS=['Sonntag','Montag','Dienstag','Mittwoch','Donnerstag','Freitag','Samstag'];
var MONTHS=['Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember'];
function tick(){{
  var n=new Date();
  var h=String(n.getHours()).padStart(2,'0');
  var m=String(n.getMinutes()).padStart(2,'0');
  document.getElementById('clock').textContent=h+':'+m;
  document.getElementById('datestr').textContent=
    DAYS[n.getDay()]+', '+n.getDate()+'. '+MONTHS[n.getMonth()]+' '+n.getFullYear();
  var hr=n.getHours();
  document.getElementById('greeting').textContent=
    hr<12?'Guten Morgen':hr<17?'Guten Tag':'Guten Abend';
}}
tick();setInterval(tick,1000);
</script>
</body></html>"""

    components.html(html_hero, height=340, scrolling=False)

    # ── CTA ───────────────────────────────────────────────────
    st.write("")
    _bc1, _bc2, _bc3 = st.columns([1, 2, 1])
    with _bc2:
        if st.button("🚀 Tag starten", use_container_width=True, key="lofi_start_btn", type="primary"):
            st.session_state.page = "Planen"
            st.rerun()
    st.write("")

    # ── Dashboard Row ─────────────────────────────────────────
    _d1, _d2, _d3 = st.columns(3)
    with _d1:
        st.markdown(stats_html, unsafe_allow_html=True)
    with _d2:
        st.markdown(deadlines_html, unsafe_allow_html=True)
    with _d3:
        st.markdown(weather_html, unsafe_allow_html=True)

    st.write("")

    # ── KI Schnellfrage ───────────────────────────────────────
    api_k = get_setting('nvidia_api_key', '')
    if api_k:
        st.markdown("### 🤖 KI Schnellfrage")
        _ki_q = st.text_input(
            "Frage", placeholder="Frag deinen KI-Coach... z.B. Wie priorisiere ich heute?",
            key="start_ki_question", label_visibility="collapsed"
        )
        if _ki_q and _ki_q != st.session_state.get('_last_ki_q', ''):
            st.session_state['_last_ki_q'] = _ki_q
            with st.spinner("KI denkt nach..."):
                try:
                    from openai import OpenAI as _OAI
                    _cli = _OAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_k)
                    _resp = _cli.chat.completions.create(
                        model="moonshotai/kimi-k2.6",
                        messages=[
                            {"role": "system", "content": "Du bist ein präziser Produktivitäts-Coach. Antworte auf Deutsch in 2-4 Sätzen, klar und direkt. Kein Fülltext."},
                            {"role": "user", "content": _ki_q}
                        ],
                        max_tokens=350, temperature=0.7
                    )
                    st.session_state['_last_ki_answer'] = _resp.choices[0].message.content
                except Exception as _e:
                    st.session_state['_last_ki_answer'] = f"Fehler: {_e}"

        if st.session_state.get('_last_ki_answer') and st.session_state.get('_last_ki_q') == _ki_q and _ki_q:
            st.markdown(f"""
<div style="background:rgba(0,212,255,0.06);border-radius:12px;padding:14px 16px;
            border-left:3px solid #00d4ff;margin-top:8px">
  <div style="font-size:9px;color:#00d4ff;letter-spacing:2px;
              text-transform:uppercase;margin-bottom:8px">KI Coach</div>
  <div style="font-size:14px;color:rgba(255,255,255,0.85);line-height:1.6">
    {st.session_state['_last_ki_answer']}</div>
</div>""", unsafe_allow_html=True)
        st.write("")

    # ── Evening Review ────────────────────────────────────────
    if total_today > 0:
        with st.expander(f"🌙 Tagesrückblick · {done_today}/{total_today} erledigt · {pct_today}%"):
            _er1, _er2, _er3 = st.columns(3)
            _er1.metric("Erledigt", f"{done_today}/{total_today}")
            _er2.metric("Quote",    f"{pct_today}%")
            _er3.metric("Offen",    total_today - done_today)

            if api_k:
                if st.button("🤖 KI-Abendreview generieren", key="start_evening_review",
                             use_container_width=True):
                    with st.spinner("KI analysiert deinen Tag..."):
                        review = ki_evening_review(api_k)
                    st.session_state['evening_review'] = review
                    st.rerun()

                if 'evening_review' in st.session_state:
                    rv = st.session_state['evening_review']
                    if 'error' in rv:
                        st.error(f"Fehler: {rv['error']}")
                    else:
                        st.markdown(f"#### {rv.get('headline', 'Tagesrückblick')}")
                        wins = rv.get('wins', [])
                        if wins:
                            st.markdown("**🏆 Wins:**")
                            for w in wins:
                                st.markdown(f"- {w}")
                        if rv.get('open_note'):
                            st.info(f"📝 {rv['open_note']}")
                        for _a in rv.get('upcoming_alerts', []):
                            st.warning(_a)
                        if rv.get('optimization_tip'):
                            st.markdown(f"**💡 Tipp für morgen:** {rv['optimization_tip']}")
                        if rv.get('tomorrow_focus'):
                            st.success(f"🎯 Morgen: **{rv['tomorrow_focus']}**")
                        if rv.get('motivation'):
                            st.markdown(f"*{rv['motivation']}*")
                        if st.button("✕ Schließen", key="close_review"):
                            del st.session_state['evening_review']
                            st.rerun()

    # ── Spontane Gedanken sortieren ─────────────────────────────
    unsorted_thoughts = get_unsorted_thoughts()
    if unsorted_thoughts:
        with st.expander(f"💭 Spontane Gedanken sortieren ({len(unsorted_thoughts)})", expanded=True):
            st.caption("Jeden Gedanken einsortieren: heute erledigen, auf ein Datum legen, oder verwerfen.")
            for th in unsorted_thoughts:
                tid = th['id']
                try:
                    ts = datetime.fromisoformat(th['created_at']).strftime('%d.%m. %H:%M')
                except Exception:
                    ts = ''
                st.markdown(
                    f'<div style="padding:8px 10px;margin:10px 0 4px 0;background:rgba(255,255,255,0.04);'
                    f'border-radius:8px 8px 0 0;border-left:3px solid #a29bfe">'
                    f'<div style="font-size:13px;color:white">{th["content"]}</div>'
                    f'<div style="font-size:10px;color:rgba(255,255,255,0.35);margin-top:2px">📝 {ts}</div>'
                    f'</div>', unsafe_allow_html=True
                )
                c1, c2, c3, c4 = st.columns([1, 1, 1.4, 0.6])
                with c1:
                    if st.button("✅ Heute", key=f"th_today_{tid}", use_container_width=True):
                        resolve_thought_to_entry(tid, th['content'], date.today().isoformat())
                        st.rerun()
                with c2:
                    if st.button("➡️ Morgen", key=f"th_tom_{tid}", use_container_width=True):
                        resolve_thought_to_entry(tid, th['content'], (date.today() + timedelta(days=1)).isoformat())
                        st.rerun()
                with c3:
                    if st.session_state.get(f"th_show_date_{tid}"):
                        d_val = st.date_input("Datum", value=date.today(), min_value=date.today(),
                                               key=f"th_date_{tid}", label_visibility="collapsed")
                        if st.button("✓ Übernehmen", key=f"th_dateconfirm_{tid}", use_container_width=True):
                            resolve_thought_to_entry(tid, th['content'], d_val.isoformat())
                            del st.session_state[f"th_show_date_{tid}"]
                            st.rerun()
                    else:
                        if st.button("📅 Datum wählen", key=f"th_pickdate_{tid}", use_container_width=True):
                            st.session_state[f"th_show_date_{tid}"] = True
                            st.rerun()
                with c4:
                    if st.button("🗑️", key=f"th_discard_{tid}", use_container_width=True):
                        discard_thought(tid)
                        st.rerun()


def render_start_page():
    render_lofi_start_page()


def _deadline_fields(form_key):
    """Renders optional deadline picker inside a form. Returns deadline string or None."""
    use_dl = st.checkbox("⏰ Deadline setzen", value=False, key=f"use_dl_{form_key}")
    if use_dl:
        dl_date = st.date_input("Deadline", value=date.today() + timedelta(days=1),
                                 min_value=date.today(), key=f"dl_{form_key}")
        return dl_date.isoformat()
    return None


def render_planen_page():
    st.title("Tag planen")
    st.caption("Drei kurze Schritte — dann direkt in den Fokus-Modus.")

    rows = get_today_entries()
    has_brain     = any(r[1] == "brain"     for r in rows)
    has_highlight = any(r[1] == "highlight" for r in rows)
    # Micro is now attached to the highlight's micro_action field
    today_highlight = next((r for r in rows if r[1] == "highlight"), None)
    has_micro       = bool(today_highlight and today_highlight[14])
    brain_rows      = [r for r in rows if r[1] == "brain"]
    # Step 4 is "ready" when all brain tasks have at least a category or micro
    has_todo_setup  = bool(brain_rows) and all(r[14] or r[15] for r in brain_rows)
    today_str       = date.today().isoformat()
    has_morning     = routine_adherence(today_str, 'morning') >= 0.999
    steps_done      = sum([has_morning, has_brain, has_highlight, has_micro])
    total_steps     = 5

    st.progress(steps_done / total_steps, text=f"Schritt {steps_done} von {total_steps} abgeschlossen")

    if steps_done >= 1:
        _, btn_col, _ = st.columns([0.35, 0.30, 0.35])
        with btn_col:
            if st.button("Tagesfokus →", key="plan_to_focus_top", use_container_width=True):
                st.session_state.page = "Tagesfokus"
                st.rerun()

    st.markdown("---")

    # Step 0: Morgenroutine
    step0_label = "✅ Morgenroutine erledigt" if has_morning else "0️⃣  Morgenroutine — Die erste Stunde"
    with st.expander(step0_label, expanded=not has_morning):
        render_morning_routine_checklist(today_str)

    # Step 1: Brain Dump
    step1_label = "✅ Brain Dump erledigt" if has_brain else "1️⃣  Brain Dump — Alles raus aus dem Kopf"
    with st.expander(step1_label, expanded=not has_brain):
        with st.form("brain_form"):
            brain_text = st.text_area("Was geht dir durch den Kopf?", height=100,
                                       placeholder="Einfach alles aufschreiben — ohne Filter")
            tags = st.text_input("Tags (optional, Komma-getrennt)")
            deadline = _deadline_fields("brain")
            if st.form_submit_button("Raus damit!"):
                if brain_text.strip():
                    add_entry("brain", brain_text.strip(), tags=tags, deadline=deadline)
                    st.rerun()

    # Step 2: Daily Highlight
    brain_texts = [r[2] for r in rows if r[1] == "brain"]
    step2_label = "✅ Daily Highlight gesetzt" if has_highlight else "2️⃣  Daily Highlight — EINE Aufgabe"
    with st.expander(step2_label, expanded=has_brain and not has_highlight):
        with st.form("highlight_form"):
            choice = st.selectbox("Aus Brain Dump wählen (optional)", [""] + brain_texts) if brain_texts else ""
            highlight = st.text_input("Highlight-Aufgabe", value=choice,
                                       placeholder="Was ist deine wichtigste Aufgabe heute?")
            tags_hl = st.text_input("Tags (optional)")
            predicted = predict_duration("highlight", tags_hl or None)
            if predicted:
                st.info(f"🤖 Basierend auf deiner Historie: ~{predicted} Minuten")
            estimate = st.number_input("Geschätzte Minuten", min_value=0, step=5, value=int(predicted or 25))
            date_input = st.date_input("Eintragsdatum", value=date.today())
            deadline_hl = _deadline_fields("hl")
            if st.form_submit_button("Als Daily Highlight setzen"):
                if highlight.strip():
                    add_entry("highlight", highlight.strip(), tags=tags_hl,
                               estimate=estimate, entry_date=date_input.isoformat(),
                               deadline=deadline_hl)
                    st.session_state.page = "Tagesfokus"
                    st.rerun()

    # Step 3: Micro-Commitment (linked to today's Highlight)
    current_micro = today_highlight[14] if today_highlight else None
    if current_micro:
        step3_label = f"✅ Micro-Commitment: \"{current_micro}\""
    else:
        step3_label = "3️⃣  Micro-Commitment — Wie startest du?"
    with st.expander(step3_label, expanded=has_highlight and not has_micro):
        if not has_highlight:
            st.info("Zuerst ein Daily Highlight setzen (Schritt 2).")
        else:
            hl_content = today_highlight[2] if today_highlight else ""
            st.markdown(f"**Aufgabe:** {hl_content}")
            st.caption("Was ist die kleinste Aktion (≤2 min) um diese Aufgabe zu starten?")
            with st.form("micro_form"):
                micro = st.text_input(
                    "Starten mit...",
                    value=current_micro or "",
                    placeholder="z.B. Dokument öffnen, E-Mail schreiben, Notiz anlegen..."
                )
                if st.form_submit_button("Speichern"):
                    if micro.strip() and today_highlight:
                        conn_mc = sqlite3.connect(DB_PATH)
                        conn_mc.execute("UPDATE entries SET micro_action=? WHERE id=?",
                                        (micro.strip(), today_highlight[0]))
                        conn_mc.commit()
                        conn_mc.close()
                        st.rerun()

    # ── Step 4: To-Do Liste einrichten ────────────────────────────
    todo_count   = len(brain_rows)
    setup_count  = sum(1 for r in brain_rows if r[14] or r[15])
    if has_todo_setup:
        step4_label = f"✅ To-Do Liste eingerichtet ({todo_count} Aufgaben)"
    elif brain_rows:
        step4_label = f"4️⃣  To-Do Liste einrichten ({setup_count}/{todo_count} bereit)"
    else:
        step4_label = "4️⃣  To-Do Liste einrichten"

    with st.expander(step4_label, expanded=has_micro and not has_todo_setup and bool(brain_rows)):
        if not brain_rows:
            st.info("Noch keine Aufgaben im Brain Dump — füge sie in Schritt 1 hinzu.")
        else:
            categories = get_categories()
            cat_opts   = ["— keine —"] + [f"{c['icon']} {c['name']}" for c in categories]
            st.caption("Für jede Aufgabe: Kategorie wählen und 2-min Starter setzen.")
            for r in brain_rows:
                eid       = r[0]
                content   = r[2]
                micro_val = r[14] or ""
                cat_id    = r[15]
                cat       = next((c for c in categories if c['id'] == cat_id), None)

                cat_html = (f'<span style="background:{cat["color"]}28;color:{cat["color"]};'
                            f'font-size:10px;font-weight:700;padding:1px 7px;border-radius:8px;'
                            f'border:1px solid {cat["color"]}44">{cat["icon"]} {cat["name"]}</span>'
                            if cat else '')
                micro_html = (f'<span style="font-size:11px;color:#00ff88"> · ⚡ {micro_val}</span>'
                              if micro_val else '')
                st.markdown(
                    f'<div style="padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.06)">'
                    f'<strong>{content}</strong> {cat_html}{micro_html}</div>',
                    unsafe_allow_html=True
                )

                with st.form(f"pl_todo_{eid}"):
                    fc1, fc2 = st.columns([1, 1])
                    with fc1:
                        cur_idx = 0
                        if cat:
                            try:
                                cur_idx = next(i+1 for i,c in enumerate(categories) if c['id'] == cat_id)
                            except StopIteration:
                                pass
                        sel_cat = st.selectbox("Kategorie", cat_opts, index=cur_idx,
                                               label_visibility="collapsed",
                                               key=f"pl_catsel_{eid}")
                    with fc2:
                        sel_micro = st.text_input("⚡ Starter (2 min)", value=micro_val,
                                                   placeholder="z.B. Tab öffnen, Datei suchen...",
                                                   label_visibility="collapsed",
                                                   key=f"pl_micro_{eid}")
                    if st.form_submit_button("Speichern", key=f"pl_save_{eid}", use_container_width=True):
                        if sel_cat != "— keine —":
                            chosen = next((c for c in categories if f"{c['icon']} {c['name']}" == sel_cat), None)
                            if chosen:
                                set_entry_category(eid, chosen['id'])
                        else:
                            set_entry_category(eid, None)
                        conn_td = sqlite3.connect(DB_PATH)
                        conn_td.execute("UPDATE entries SET micro_action=? WHERE id=?",
                                        (sel_micro.strip() or None, eid))
                        conn_td.commit()
                        conn_td.close()
                        st.rerun()

            st.markdown("---")
            if st.button("✅ Fertig — zum Tagesfokus", key="plan_step4_done", use_container_width=True):
                st.session_state.page = "Tagesfokus"
                st.rerun()

    # ── KI Tag analysieren ────────────────────────────────────────
    st.markdown("---")
    api_key_plan = get_setting('nvidia_api_key', '')
    if api_key_plan and brain_rows:
        st.markdown("### 🧠 KI-Tagesanalyse")
        st.caption("KI analysiert alle deine Aufgaben, zerlegt sie in Mikro-Schritte und erkennt morgen Termine für Vorbereitungen heute.")
        col_ana, col_info = st.columns([1, 2])
        with col_ana:
            if st.button("🔍 Tag analysieren", key="plan_analyze_day", use_container_width=True):
                with st.spinner("KI analysiert deinen Tag..."):
                    result = ki_analyze_full_day(api_key_plan)
                st.session_state['day_analysis'] = result
                st.rerun()
        with col_info:
            if 'day_analysis' in st.session_state and 'day_summary' in st.session_state['day_analysis']:
                st.info(f"📋 {st.session_state['day_analysis']['day_summary']}")

        if 'day_analysis' in st.session_state:
            da = st.session_state['day_analysis']
            if 'error' in da:
                st.error(f"Fehler: {da['error']}")
            else:
                tasks_analyzed = da.get('tasks', [])
                prep_tasks     = da.get('prep_tasks', [])
                total_min      = da.get('total_estimated_minutes', 0)
                focus_order    = da.get('focus_order', [])

                if total_min:
                    h, m = divmod(total_min, 60)
                    st.caption(f"⏱️ Geschätzte Gesamtzeit: {h}h {m}min")

                if focus_order:
                    order_names = []
                    entry_map = {r[0]: r[2] for r in brain_rows}
                    for eid in focus_order[:5]:
                        if eid in entry_map:
                            order_names.append(entry_map[eid][:35])
                    if order_names:
                        st.caption("🎯 Empfohlene Reihenfolge: " + " → ".join(order_names))

                if tasks_analyzed:
                    if st.button(f"✅ Mikro-Schritte für {len(tasks_analyzed)} Aufgaben speichern",
                                 key="plan_save_analysis", use_container_width=True):
                        saved = 0
                        for t in tasks_analyzed:
                            eid   = t.get('entry_id')
                            steps = t.get('steps', [])
                            if eid and steps:
                                save_task_steps(eid, steps)
                                save_task_analysis(
                                    eid,
                                    t.get('summary', ''),
                                    t.get('real_estimate_minutes', 0),
                                    t.get('context_note', '')
                                )
                            saved += 1
                        # Add prep tasks
                        prep_added = 0
                        categories_all = get_categories()
                        for pt in prep_tasks:
                            cat_name = pt.get('category', '')
                            cat_obj  = next((c for c in categories_all if c['name'] == cat_name), None)
                            new_id   = add_entry(
                                "brain", pt['content'],
                                estimate=pt.get('estimate_minutes', 10),
                                entry_date=pt.get('date', date.today().isoformat())
                            )
                            if new_id:
                                if cat_obj:
                                    set_entry_category(new_id, cat_obj['id'])
                                micro = pt.get('micro_action', '').strip()
                                if micro:
                                    conn_pp = sqlite3.connect(DB_PATH)
                                    conn_pp.execute("UPDATE entries SET micro_action=? WHERE id=?",
                                                    (micro, new_id))
                                    conn_pp.commit()
                                    conn_pp.close()
                                prep_added += 1
                        del st.session_state['day_analysis']
                        st.success(f"✅ {saved} Aufgaben analysiert, {prep_added} Vorbereitungsaufgaben hinzugefügt!")
                        st.rerun()

    # ── KI Aufgabenplaner ─────────────────────────────────────────
    st.markdown("---")
    api_key_plan = get_setting('nvidia_api_key', '')
    if not api_key_plan:
        with st.expander("🤖 KI-Aufgabenplaner (API-Key nötig)"):
            st.caption("Einmal hinterlegen — dann auf allen Seiten verfügbar.")
            with st.form("plan_api_key_form"):
                k = st.text_input("NVIDIA API Key", type="password", placeholder="nvapi-...", key="plan_api_key_input")
                if st.form_submit_button("Speichern"):
                    if k.strip():
                        set_setting('nvidia_api_key', k.strip())
                        st.rerun()
    else:
        render_ki_planner_section(api_key_plan)


HABIT_ICONS = ["💧","🏋️","📚","🧘","🏃","✍️","🎯","🍎","😴","💊","🌿","🎵","💻","🙏","❤️","🌞",
               "🥗","🧠","🦷","🛁","📝","🎨","🎤","🏊","🚴","🤸","🧹","🛌","📞","💰"]


def adaptive_score(completion_pct, energy_pct):
    """50% Energie + 50% Completion = 100% adaptiver Score."""
    if energy_pct <= 0:
        return 0
    return round(completion_pct / energy_pct * 100)


def get_habit_streak(habit_id):
    today_d = date.today()
    logs = get_habit_logs_range(habit_id, 365)
    log_dict = {l['log_date']: adaptive_score(l['completion_pct'], l['energy_level']) for l in logs}

    current = 0
    for i in range(365):
        d = (today_d - timedelta(days=i)).isoformat()
        s = log_dict.get(d, -1)
        if s == -1:
            if i == 0:
                continue
            break
        if s >= 80:
            current += 1
        else:
            if i > 0:
                break

    best = tmp = 0
    prev_d = None
    for ld in sorted(log_dict.keys()):
        if log_dict[ld] >= 80:
            if prev_d and (date.fromisoformat(ld) - date.fromisoformat(prev_d)).days == 1:
                tmp += 1
            else:
                tmp = 1
            best = max(best, tmp)
        else:
            tmp = 0
        prev_d = ld
    return current, best


def _habit_ring_html(habit, score, completion_pct):
    r, cx, cy = 36, 44, 44
    circ = 2 * 3.14159265 * r
    off = circ * (1 - min(100, completion_pct) / 100)

    if score >= 120:
        ring_col = "#ff00ff"; glow = "0 0 14px #ff00ff,0 0 28px #ff00ff55"
    elif score >= 100:
        ring_col = "#00ff88"; glow = "0 0 10px #00ff88,0 0 20px #00ff8855"
    elif score >= 80:
        ring_col = habit['color']; glow = f"0 0 8px {habit['color']}"
    elif score >= 50:
        ring_col = "#ffd700"; glow = ""
    elif score >= 25:
        ring_col = "#ff9500"; glow = ""
    else:
        ring_col = "rgba(255,255,255,0.18)"; glow = ""

    flt = f"drop-shadow({glow})" if glow else "none"

    score_badge = ""
    if score >= 120:
        score_badge = f'<text x="{cx}" y="{cy+15}" text-anchor="middle" dominant-baseline="middle" font-size="9" fill="#ff00ff" font-weight="900">ÜBER-POWER!</text>'
    elif score >= 100:
        score_badge = f'<text x="{cx}" y="{cy+15}" text-anchor="middle" dominant-baseline="middle" font-size="9" fill="#00ff88" font-weight="900">100%+ 🚀</text>'
    else:
        score_badge = f'<text x="{cx}" y="{cy+15}" text-anchor="middle" dominant-baseline="middle" font-size="11" fill="{ring_col}" font-weight="700">{score}%</text>'

    return f"""<div style="display:flex;flex-direction:column;align-items:center;gap:5px;padding:4px 0">
<svg width="88" height="88" style="filter:{flt};overflow:visible">
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="rgba(255,255,255,0.07)" stroke-width="7"/>
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{ring_col}" stroke-width="7"
    stroke-linecap="round" stroke-dasharray="{circ:.1f}" stroke-dashoffset="{off:.1f}"
    transform="rotate(-90 {cx} {cy})"/>
  <text x="{cx}" y="{cy-5}" text-anchor="middle" dominant-baseline="middle" font-size="22">{habit['icon']}</text>
  {score_badge}
</svg>
<div style="font-size:12px;text-align:center;color:rgba(255,255,255,0.85);max-width:88px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{habit['name']}</div>
</div>"""


def _habit_heatmap_html(habit, days=84):
    today_d = date.today()
    logs = get_habit_logs_range(habit['id'], days)
    log_dict = {l['log_date']: adaptive_score(l['completion_pct'], l['energy_level']) for l in logs}
    current_streak, best_streak = get_habit_streak(habit['id'])

    def cell_color(s):
        if s is None: return "rgba(255,255,255,0.05)"
        if s >= 120: return "#ff00ff"
        if s >= 100: return "#00ff88"
        if s >= 80: return habit['color']
        if s >= 50: return "#ffd700"
        if s >= 25: return "#ff9500"
        if s > 0: return "#ff4444"
        return "rgba(255,255,255,0.05)"

    cells = ""
    for i in range(days - 1, -1, -1):
        d = today_d - timedelta(days=i)
        s = log_dict.get(d.isoformat(), None)
        c = cell_color(s)
        tip = f"{d.strftime('%d.%m')}: {s}%" if s is not None else f"{d.strftime('%d.%m')}: —"
        cells += f'<div title="{tip}" style="width:14px;height:14px;background:{c};border-radius:2px;flex-shrink:0"></div>'

    fire_badge = f'<span style="background:linear-gradient(135deg,#ff6b00,#ffcc00);color:#000;font-size:11px;font-weight:800;padding:2px 8px;border-radius:20px">🔥 {current_streak}</span>' if current_streak > 0 else '<span style="color:rgba(255,255,255,0.3);font-size:12px">0 Tage Streak</span>'
    best_txt = f'<span style="color:rgba(255,255,255,0.35);font-size:11px">· Rekord: {best_streak} 🏆</span>' if best_streak > 0 else ""

    return f"""<div style="background:rgba(255,255,255,0.03);border-radius:12px;padding:14px 16px;
  border:1px solid rgba(255,255,255,0.07);margin-bottom:10px">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap">
    <span style="font-size:20px">{habit['icon']}</span>
    <span style="font-weight:600;color:white;font-size:13px">{habit['name']}</span>
    {fire_badge} {best_txt}
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:3px;width:calc(14*(14px + 3px))">
    {cells}
  </div>
  <div style="display:flex;gap:8px;align-items:center;margin-top:8px;font-size:10px;color:rgba(255,255,255,0.3)">
    <span>wenig</span>
    <div style="width:10px;height:10px;background:#ff4444;border-radius:2px"></div>
    <div style="width:10px;height:10px;background:#ff9500;border-radius:2px"></div>
    <div style="width:10px;height:10px;background:{habit['color']};border-radius:2px"></div>
    <div style="width:10px;height:10px;background:#00ff88;border-radius:2px"></div>
    <div style="width:10px;height:10px;background:#ff00ff;border-radius:2px"></div>
    <span>mehr / Über-Power</span>
  </div>
</div>"""


def _render_habit_streaks(habits):
    streak_data = []
    for h in habits:
        cur, best = get_habit_streak(h['id'])
        logs30 = get_habit_logs_range(h['id'], 30)
        high = sum(1 for l in logs30 if adaptive_score(l['completion_pct'], l['energy_level']) >= 80)
        streak_data.append({'h': h, 'cur': cur, 'best': best, 'consistency': round(high / 30 * 100)})
    streak_data.sort(key=lambda x: -x['cur'])

    for s in streak_data:
        h, cur, best, cons = s['h'], s['cur'], s['best'], s['consistency']
        fire_count = min(5, max(1, cur // 3)) if cur > 0 else 0
        fires = "🔥" * fire_count

        if cur == 0: lvl, lc = "Noch nicht gestartet", "#666"
        elif cur < 3: lvl, lc = "Aufwärmen", "#ff9500"
        elif cur < 7: lvl, lc = "Im Fluss", "#ffd700"
        elif cur < 14: lvl, lc = "Auf Kurs", "#00d4ff"
        elif cur < 30: lvl, lc = "🔥 Unaufhaltsam", "#00ff88"
        else: lvl, lc = "👑 LEGEND", "#ff00ff"

        st.markdown(f"""<div style="display:flex;align-items:center;gap:16px;padding:14px 18px;
            background:rgba(255,255,255,0.04);border-radius:12px;
            border:1px solid rgba(255,255,255,0.08);margin-bottom:10px;
            border-left:4px solid {h['color']}">
          <span style="font-size:32px">{h['icon']}</span>
          <div style="flex:1;min-width:0">
            <div style="font-weight:600;color:white;font-size:14px">{h['name']}</div>
            <div style="color:rgba(255,255,255,0.4);font-size:12px;margin-top:3px">
              30-Tage-Konsistenz: <strong style="color:rgba(255,255,255,0.7)">{cons}%</strong> ·
              Rekord: <strong style="color:rgba(255,255,255,0.7)">{best} Tage</strong>
            </div>
          </div>
          <div style="text-align:center;min-width:80px">
            <div style="font-size:28px;line-height:1.1">{fires if cur > 0 else "⭕"}</div>
            <div style="font-size:28px;font-weight:900;color:{lc};line-height:1.2">{cur}</div>
            <div style="font-size:10px;color:{lc};font-weight:700;text-transform:uppercase;letter-spacing:1px">{lvl}</div>
          </div>
        </div>""", unsafe_allow_html=True)


def _render_habit_radar(habits):
    today_d = date.today()
    names, scores = [], []
    for h in habits:
        week_sc = []
        for i in range(7):
            d = (today_d - timedelta(days=i)).isoformat()
            log = get_habit_log(h['id'], d)
            if log:
                week_sc.append(adaptive_score(log['completion_pct'], log['energy_level']))
        avg = sum(week_sc) / max(len(week_sc), 1) if week_sc else 0
        names.append(h['icon'] + ' ' + h['name'])
        scores.append(avg)

    if len(habits) < 3:
        st.info("Mindestens 3 Habits für den Radar benötigt.")
        return

    sc = scores + [scores[0]]
    nm = names + [names[0]]
    fig = go.Figure(go.Scatterpolar(
        r=sc, theta=nm, fill='toself',
        fillcolor='rgba(0,212,255,0.12)',
        line=dict(color='#00d4ff', width=2.5),
        marker=dict(size=7, color='#00d4ff')
    ))
    fig.update_layout(
        polar=dict(
            bgcolor='rgba(0,0,0,0)',
            radialaxis=dict(visible=True, range=[0, 120],
                            gridcolor='rgba(255,255,255,0.1)',
                            linecolor='rgba(255,255,255,0.1)',
                            tickfont=dict(color='rgba(255,255,255,0.35)', size=9)),
            angularaxis=dict(gridcolor='rgba(255,255,255,0.1)',
                             linecolor='rgba(255,255,255,0.1)',
                             tickfont=dict(color='white', size=11))
        ),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'), showlegend=False,
        margin=dict(t=30, b=30, l=60, r=60), height=400
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("7-Tage-Durchschnitt · 100% = Ziel bei gegebener Energie vollständig erreicht")


def _render_habit_momentum(habits):
    today_d = date.today()
    COLORS = ['#00d4ff','#ff6b6b','#ffd700','#00ff88','#ff00ff','#ff9500','#7fff00']
    fig = go.Figure()

    for i, h in enumerate(habits):
        logs = get_habit_logs_range(h['id'], 37)
        log_dict = {l['log_date']: adaptive_score(l['completion_pct'], l['energy_level']) for l in logs}
        dates, avgs = [], []
        for j in range(29, -1, -1):
            d = today_d - timedelta(days=j)
            window = [log_dict[(d - timedelta(days=k)).isoformat()]
                      for k in range(7) if (d - timedelta(days=k)).isoformat() in log_dict]
            dates.append(d.isoformat())
            avgs.append(round(sum(window) / len(window), 1) if window else 0)

        col = COLORS[i % len(COLORS)]
        fig.add_trace(go.Scatter(
            x=dates, y=avgs, mode='lines',
            name=h['icon'] + ' ' + h['name'],
            line=dict(color=col, width=2.5),
            fill='tozeroy', fillcolor=f'rgba({int(col[1:3],16)},{int(col[3:5],16)},{int(col[5:7],16)},0.09)'
        ))

    fig.add_hline(y=80, line_dash="dot", line_color="rgba(255,255,255,0.25)",
                   annotation_text="80% Ziel", annotation_position="right",
                   annotation_font=dict(color="rgba(255,255,255,0.4)", size=10))
    fig.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(5,8,15,0.4)',
        yaxis=dict(title='Adapt. Score', range=[0, 130], gridcolor='rgba(255,255,255,0.05)'),
        xaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
        hovermode='x unified', margin=dict(t=10, b=40, l=50, r=20), height=340,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0)
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("7-Tage gleitender Durchschnitt des adaptiven Scores · Strichlinie = 80% Schwelle")


def _clear_focus_mode():
    for k in ['focus_task_id', 'focus_task_name', 'focus_task_estimate',
              'focus_phase', 'focus_round', 'focus_pomodoro_start',
              'focus_total_seconds', 'focus_ki_review', 'focus_status',
              'focus_blocker', 'focus_run_ki']:
        if k in st.session_state:
            del st.session_state[k]


def _render_focus_mode():
    phase = st.session_state.get('focus_phase', 'confirm')
    task_id = st.session_state.get('focus_task_id')
    task_name = st.session_state.get('focus_task_name', '?')
    task_estimate = st.session_state.get('focus_task_estimate', 25)

    st.markdown("""<style>
    .focus-hdr{text-align:center;font-size:12px;letter-spacing:3px;text-transform:uppercase;
               color:#00d4ff;opacity:.7;padding:10px 0 4px}
    .focus-task{text-align:center;font-size:22px;font-weight:700;padding:8px 0 16px}
    .pomo-time{text-align:center;font-size:76px;font-weight:900;color:#00d4ff;
               letter-spacing:4px;line-height:1;padding:16px 0}
    </style>""", unsafe_allow_html=True)

    _, center, _ = st.columns([0.5, 3, 0.5])

    # ── Phase 1: Anti-Distraktion Bestätigung ──────────────────────
    if phase == 'confirm':
        with center:
            st.markdown('<div class="focus-hdr">🎯 Fokus Modus</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="focus-task">{task_name}</div>', unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("##### Bevor du startest:")
            c1 = st.checkbox("📵 Handy auf lautlos / umgedreht", key="fc_phone")
            c2 = st.checkbox("🔕 Benachrichtigungen aus", key="fc_notif")
            c3 = st.checkbox("💻 Unnötige Tabs geschlossen", key="fc_tabs")
            c4 = st.checkbox("💧 Wasser/Kaffee dabei", key="fc_water")
            st.write("")
            if c1 and c2 and c3 and c4:
                if st.button("🚀 JETZT STARTEN", use_container_width=True, type="primary"):
                    start_task(task_id)
                    st.session_state.focus_phase = 'pomodoro'
                    st.session_state.focus_round = 1
                    st.session_state.focus_pomodoro_start = datetime.utcnow().isoformat()
                    st.session_state.focus_total_seconds = 0
                    st.rerun()
            else:
                st.button("✅ Alle Häkchen setzen zum Starten", disabled=True, use_container_width=True)
            st.write("")
            if st.button("← Abbrechen", use_container_width=True, key="fc_cancel_confirm"):
                _clear_focus_mode()
                st.rerun()

    # ── Phase 2: Pomodoro Countdown ─────────────────────────────────
    elif phase == 'pomodoro':
        round_num = st.session_state.get('focus_round', 1)
        start_str = st.session_state.get('focus_pomodoro_start', datetime.utcnow().isoformat())
        try:
            elapsed = int((datetime.utcnow() - datetime.fromisoformat(start_str)).total_seconds())
        except Exception:
            elapsed = 0
        remaining = max(0, POMODORO_DURATION - elapsed)
        mins, secs = remaining // 60, remaining % 60
        pct = min(1.0, elapsed / POMODORO_DURATION)

        with center:
            st.markdown(f'<div class="focus-hdr">🎯 FOKUS — Runde {round_num}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="focus-task">{task_name}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="pomo-time">{mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)
            st.progress(pct)
            if remaining == 0:
                st.success("⏰ 25 Minuten voll! Wie weiter?")
            st.write("")
            btn1, btn2, btn3, btn4 = st.columns(4)
            with btn1:
                if st.button("✅ Aufgabe fertig", use_container_width=True, type="primary"):
                    done_secs = st.session_state.get('focus_total_seconds', 0) + (POMODORO_DURATION - remaining)
                    toggle_done(task_id, True, elapsed_seconds=done_secs,
                                points=compute_points(done_secs, task_estimate))
                    st.session_state.focus_phase = 'review'
                    st.session_state.focus_total_seconds = done_secs
                    st.rerun()
            with btn2:
                if st.button("🔄 Noch eine Runde", use_container_width=True):
                    prev = st.session_state.get('focus_total_seconds', 0)
                    st.session_state.focus_total_seconds = prev + (POMODORO_DURATION - remaining)
                    st.session_state.focus_round = round_num + 1
                    st.session_state.focus_pomodoro_start = datetime.utcnow().isoformat()
                    st.rerun()
            with btn3:
                if st.button("🧺 Haushalts-Pause", use_container_width=True):
                    prev = st.session_state.get('focus_total_seconds', 0)
                    st.session_state.focus_total_seconds = prev + (POMODORO_DURATION - remaining)
                    st.session_state.focus_phase = 'household_break'
                    st.rerun()
            with btn4:
                if st.button("🚫 Abbrechen", use_container_width=True):
                    _clear_focus_mode()
                    st.rerun()

        if remaining > 0:
            time.sleep(1)
            st.rerun()

    # ── Phase 2b: Haushalts-Pause ─────────────────────────────────
    elif phase == 'household_break':
        suggestion = suggest_household_break_tasks()
        pick = suggestion['tasks'][0] if suggestion['tasks'] else None

        with center:
            st.markdown('<div class="focus-hdr">🧺 Haushalts-Pause</div>', unsafe_allow_html=True)
            if pick:
                st.markdown(f'<div class="focus-task">{pick["icon"]} {pick["label"]}</div>', unsafe_allow_html=True)
                st.caption(f"~{pick['est_minutes']} Min · passt ins heutige Zeitbudget "
                          f"({suggestion['budget_minutes']} Min)")
            else:
                st.markdown('<div class="focus-task">🎉 Nichts dringend fällig</div>', unsafe_allow_html=True)
                st.caption("Mach trotzdem kurz Beine — z.B. strecken, Wasser holen, durchlüften.")
            st.write("")
            b1, b2 = st.columns(2)
            with b1:
                if st.button("✅ Erledigt, weiter geht's", use_container_width=True, type="primary"):
                    if pick:
                        log_household_task(pick['key'])
                    st.session_state.focus_round = st.session_state.get('focus_round', 1) + 1
                    st.session_state.focus_pomodoro_start = datetime.utcnow().isoformat()
                    st.session_state.focus_phase = 'pomodoro'
                    st.rerun()
            with b2:
                if st.button("⏭️ Ohne Pause weiter", use_container_width=True):
                    st.session_state.focus_round = st.session_state.get('focus_round', 1) + 1
                    st.session_state.focus_pomodoro_start = datetime.utcnow().isoformat()
                    st.session_state.focus_phase = 'pomodoro'
                    st.rerun()

    # ── Phase 3: KI Review ──────────────────────────────────────────
    elif phase == 'review':
        round_num = st.session_state.get('focus_round', 1)
        total_secs = st.session_state.get('focus_total_seconds', 0)
        total_mins = max(1, total_secs // 60)

        with center:
            st.markdown('<div class="focus-hdr">✅ SESSION BEENDET</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="focus-task">{task_name}</div>', unsafe_allow_html=True)
            st.markdown(f"**Gearbeitet:** {total_mins} Min · {round_num} {'Runde' if round_num == 1 else 'Runden'}")
            st.markdown("---")

            if not st.session_state.get('focus_ki_review') and not st.session_state.get('focus_run_ki'):
                st.markdown("##### Status-Update für deinen KI Coach:")
                with st.form("focus_review_form"):
                    status = st.text_area("Wo stehst du? Was wurde geschafft?", height=100,
                                           placeholder="z.B. 'Hälfte der Implementierung fertig, noch Bugfixes offen'")
                    blocker = st.text_area("Was blockiert dich? (optional)", height=60,
                                            placeholder="z.B. 'Technisches Problem mit Y'")
                    if st.form_submit_button("🤖 KI Analyse starten", use_container_width=True):
                        st.session_state.focus_status = status
                        st.session_state.focus_blocker = blocker
                        st.session_state.focus_run_ki = True
                        st.rerun()

            if st.session_state.get('focus_run_ki') and not st.session_state.get('focus_ki_review'):
                if 'focus_run_ki' in st.session_state:
                    del st.session_state['focus_run_ki']
                api_key = get_setting('nvidia_api_key', '')
                if api_key:
                    try:
                        from openai import OpenAI as _OpenAI
                        client = _OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)
                        context = build_ai_context(days_back=0)
                        status = st.session_state.get('focus_status', '')
                        blocker = st.session_state.get('focus_blocker', '')
                        msgs = [
                            {"role": "system", "content": "Du bist ein ADHS-Coach. Antworte kurz, direkt, auf Deutsch."},
                            {"role": "user", "content": (
                                f"Fokus-Session beendet.\n"
                                f"Aufgabe: {task_name}\n"
                                f"Gearbeitet: {total_mins} Min ({round_num} Runden)\n"
                                f"Status: {status}\nBlocker: {blocker or 'keiner'}\n\n"
                                f"Kontext:\n{context}\n\n"
                                "Antworte mit genau:\n"
                                "**Wo du stehst:** (1-2 Sätze)\n"
                                "**Nächster Schritt morgen:** (1 konkrete Aktion)\n"
                                "**Geschätzte Zeit:** (X Minuten)\n"
                                "Max. 80 Wörter."
                            )}
                        ]
                        placeholder_ki = st.empty()
                        ki_text = _ki_stream(client, msgs, placeholder_ki, max_tokens=250)
                        st.session_state.focus_ki_review = ki_text
                        st.rerun()
                    except Exception as e:
                        st.error(f"KI Fehler: {e}")
                else:
                    st.warning("Kein NVIDIA API Key gesetzt — geh zu 'KI Coach' um einen einzutragen.")

            if st.session_state.get('focus_ki_review'):
                st.markdown("##### 🤖 KI Coach:")
                st.info(st.session_state.focus_ki_review)
                st.write("")
                ca, cb = st.columns(2)
                with ca:
                    if st.button("📅 Nächsten Schritt für morgen einplanen", use_container_width=True, type="primary"):
                        tomorrow_str = (date.today() + timedelta(days=1)).isoformat()
                        add_entry("brain", f"Weiter: {task_name}", tags="fokus,follow-up",
                                  estimate=30, entry_date=tomorrow_str)
                        st.success("✅ Für morgen eingeplant!")
                with cb:
                    if st.button("Fertig → Tagesfokus", use_container_width=True):
                        _clear_focus_mode()
                        st.session_state.page = "Tagesfokus"
                        st.rerun()
            elif not st.session_state.get('focus_run_ki'):
                if st.button("← Ohne KI Review zurück", use_container_width=True):
                    _clear_focus_mode()
                    st.session_state.page = "Tagesfokus"
                    st.rerun()


def render_tagesfokus_page():
    st.markdown(URGENCY_CSS, unsafe_allow_html=True)

    today = date.today()
    today_label = f"{WOCHENTAGE[today.weekday()]}, {today.day}. {MONATE[today.month - 1]} {today.year}"

    t_col, b_col = st.columns([0.85, 0.15])
    with t_col:
        st.title(f"Tagesfokus · {today_label}")
    with b_col:
        st.write("")
        if st.button("← Planen", key="fok_back"):
            st.session_state.page = "Planen"
            st.rerun()

    rows = get_today_entries()
    total      = len(rows)
    done_count = sum(1 for r in rows if r[9])
    pts_today  = sum(r[6] for r in rows)
    pct        = done_count / total if total > 0 else 0

    components.html(
        _build_tagesfokus_hero(done_count, total, pts_today, today_label),
        height=240
    )
    st.markdown("---")

    # ── Haushalts-Pausen-Vorschlag (Deadline-bewusst) ──────────────
    hh_suggestion = suggest_household_break_tasks()
    with st.expander(f"🏡 Haushalts-Pause heute (~{hh_suggestion['budget_minutes']} Min Zeitbudget)",
                     expanded=False):
        if hh_suggestion['tasks']:
            for t in hh_suggestion['tasks']:
                c1, c2 = st.columns([0.78, 0.22])
                with c1:
                    st.markdown(f"{t['icon']} **{t['label']}** (~{t['est_minutes']} Min)"
                               + (" 🔴 überfällig" if t['overdue'] else ""), unsafe_allow_html=True)
                with c2:
                    if st.button("✅ Erledigt", key=f"tf_hh_{t['key']}", use_container_width=True):
                        log_household_task(t['key'])
                        st.rerun()
        else:
            st.success("Heute ist nichts dringend fällig. 🎉")
        if st.button("🏡 Zur Haushalt-Seite →", key="tf_hh_goto", use_container_width=True):
            st.session_state.page = "Haushalt"
            st.rerun()

    if not rows:
        st.info("Noch keine Aufgaben für heute — starte mit dem Tag planen.")
        if st.button("Tag planen →", key="fok_goto_planen"):
            st.session_state.page = "Planen"
            st.rerun()
        return

    highlights = [r for r in rows if r[1] == "highlight"]
    brains     = [r for r in rows if r[1] in ("brain", "micro")]
    categories = get_categories()
    cat_map    = {c['id']: c for c in categories}

    def _set_micro(entry_id, text):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE entries SET micro_action=? WHERE id=?", (text or None, entry_id))
        conn.commit()
        conn.close()

    def render_row(r, css_class, pfx, show_category_controls=True):
        eid, etype, content, tags, priority, estimate, points, created_at, entry_date, done, \
            completed_at, elapsed_seconds, started_at, deadline, micro_action, category_id = r
        urg_level, urg_days, urg_label, urg_class = get_urgency(deadline)
        cat = cat_map.get(category_id)

        card_cls = f"{css_class} fok-done" if done else css_class
        dl_html = f'<span class="dl-badge">{urg_label}</span>' if urg_label and not done else ""
        cat_html = (f'<span style="background:{cat["color"]}28;color:{cat["color"]};'
                    f'font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;'
                    f'border:1px solid {cat["color"]}55;margin-left:6px">'
                    f'{cat["icon"]} {cat["name"]}</span>' if cat and not done else "")
        micro_html = (f'<br><span style="font-size:11px;color:#00ff88;opacity:.9">'
                      f'⚡ Starten mit: <em>{micro_action}</em></span>'
                      if micro_action and not done else "")

        # ── Steps progress inline ──
        steps = get_task_steps(eid)
        steps_html = ""
        if steps and not done:
            done_s  = sum(1 for s in steps if s['done'])
            total_s = len(steps)
            next_step_idx = next((i for i, s in enumerate(steps) if not s['done']), None)
            dots = ""
            for i, s in enumerate(steps):
                if s['done']:
                    dots += '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#00d4ff;box-shadow:0 0 7px #00d4ff,0 0 14px rgba(0,212,255,.4);margin-right:4px"></span>'
                elif i == next_step_idx:
                    # current step — pulsing
                    dots += '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#a29bfe;box-shadow:0 0 8px #a29bfe,0 0 18px rgba(162,155,254,.5);margin-right:4px;animation:dot-pulse 1.4s ease-in-out infinite"></span>'
                else:
                    dots += '<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.15);margin-right:4px"></span>'
            steps_html = (
                f'<div style="margin-top:8px;display:flex;align-items:center;gap:4px">'
                f'<style>@keyframes dot-pulse{{0%,100%{{box-shadow:0 0 8px #a29bfe,0 0 18px rgba(162,155,254,.5)}}50%{{box-shadow:0 0 14px #a29bfe,0 0 30px rgba(162,155,254,.8)}}}}</style>'
                f'{dots}'
                f'<span style="font-size:10px;color:rgba(255,255,255,.35);margin-left:6px">{done_s}/{total_s}</span>'
                f'</div>'
            )
        analysis = get_task_analysis(eid)
        analysis_html = ""
        if analysis and analysis.get('context_note') and not done:
            analysis_html = (f'<div style="font-size:10px;color:rgba(255,255,255,.35);'
                             f'margin-top:4px;font-style:italic">{analysis["context_note"]}</div>')

        st.markdown(
            f'<div class="{card_cls}"><strong>{content}</strong>{dl_html}{cat_html}{micro_html}'
            + (f'<br><small style="opacity:.55">ca. {estimate} min</small>' if estimate else "")
            + steps_html + analysis_html
            + "</div>", unsafe_allow_html=True
        )

        c_chk, c_btn, c_fok, _ = st.columns([0.08, 0.18, 0.16, 0.58])
        with c_chk:
            new_done = st.checkbox("", value=bool(done), key=f"{pfx}_chk_{eid}",
                                   label_visibility="collapsed")
            if new_done != bool(done):
                elapsed = 0
                if started_at:
                    try:
                        sa = datetime.fromisoformat(started_at)
                        elapsed = int((datetime.utcnow() - sa).total_seconds())
                    except Exception:
                        pass
                if new_done:
                    toggle_done(eid, True, elapsed_seconds=elapsed,
                                points=compute_points(elapsed, estimate))
                else:
                    toggle_done(eid, False, elapsed_seconds=0)
                st.rerun()
        with c_btn:
            if not done:
                if started_at:
                    if st.button("Stop & ✓", key=f"{pfx}_stop_{eid}"):
                        elapsed = 0
                        try:
                            sa = datetime.fromisoformat(started_at)
                            elapsed = int((datetime.utcnow() - sa).total_seconds())
                        except Exception:
                            pass
                        toggle_done(eid, True, elapsed_seconds=elapsed,
                                    points=compute_points(elapsed, estimate))
                        st.rerun()
                else:
                    if st.button("Start", key=f"{pfx}_start_{eid}"):
                        start_task(eid)
                        st.rerun()
        with c_fok:
            if not done:
                if st.button("🎯 Fokus", key=f"{pfx}_fok_{eid}", use_container_width=True):
                    st.session_state.focus_task_id = eid
                    st.session_state.focus_task_name = content
                    st.session_state.focus_task_estimate = estimate or 25
                    st.session_state.focus_phase = 'confirm'
                    st.rerun()

        # Inline editors: Micro + Kategorie
        if not done:
            btn_cols = st.columns(2)
            with btn_cols[0]:
                micro_lbl = "⚡ Micro ändern" if micro_action else "⚡ Micro setzen"
                if st.button(micro_lbl, key=f"{pfx}_mshow_{eid}", use_container_width=True):
                    st.session_state[f"show_micro_{eid}"] = not st.session_state.get(f"show_micro_{eid}", False)
                    st.rerun()
            if show_category_controls:
                with btn_cols[1]:
                    cat_lbl = f"🏷️ {cat['icon']} {cat['name']}" if cat else "🏷️ Kategorie"
                    if st.button(cat_lbl, key=f"{pfx}_cshow_{eid}", use_container_width=True):
                        st.session_state[f"show_cat_{eid}"] = not st.session_state.get(f"show_cat_{eid}", False)
                        st.rerun()

            if st.session_state.get(f"show_micro_{eid}"):
                new_micro = st.text_input(
                    "⚡ Starten mit (2 min):", value=micro_action or "",
                    placeholder="z.B. Dokument öffnen, Notiz anlegen...",
                    key=f"{pfx}_micro_inp_{eid}"
                )
                sc, cc = st.columns(2)
                with sc:
                    if st.button("💾 Speichern", key=f"{pfx}_msave_{eid}", use_container_width=True):
                        _set_micro(eid, new_micro.strip())
                        st.session_state[f"show_micro_{eid}"] = False
                        st.rerun()
                with cc:
                    if st.button("✕", key=f"{pfx}_mcancel_{eid}", use_container_width=True):
                        st.session_state[f"show_micro_{eid}"] = False
                        st.rerun()

            if show_category_controls and st.session_state.get(f"show_cat_{eid}"):
                cat_options = ["— keine —"] + [f"{c['icon']} {c['name']}" for c in categories]
                cur_idx = 0
                if cat:
                    try:
                        cur_idx = next(i+1 for i,c in enumerate(categories) if c['id'] == category_id)
                    except StopIteration:
                        pass
                sel = st.selectbox("Kategorie wählen:", cat_options, index=cur_idx,
                                   key=f"{pfx}_catsel_{eid}")
                sc2, cc2 = st.columns(2)
                with sc2:
                    if st.button("💾 Speichern", key=f"{pfx}_csave_{eid}", use_container_width=True):
                        if sel == "— keine —":
                            set_entry_category(eid, None)
                        else:
                            chosen = next((c for c in categories
                                           if f"{c['icon']} {c['name']}" == sel), None)
                            if chosen:
                                set_entry_category(eid, chosen['id'])
                        st.session_state[f"show_cat_{eid}"] = False
                        st.rerun()
                with cc2:
                    if st.button("✕", key=f"{pfx}_ccancel_{eid}", use_container_width=True):
                        st.session_state[f"show_cat_{eid}"] = False
                        st.rerun()

        # ── Steps Checklist ──────────────────────────────────────
        if steps and not done:
            with st.expander(
                f"📋 Schritte ({sum(1 for s in steps if s['done'])}/{len(steps)})",
                expanded=st.session_state.get(f"steps_open_{eid}", False)
            ):
                for s in steps:
                    scol1, scol2 = st.columns([0.06, 0.94])
                    with scol1:
                        step_done = st.checkbox(
                            "", value=s['done'],
                            key=f"{pfx}_step_{s['id']}",
                            label_visibility="collapsed"
                        )
                        if step_done != s['done']:
                            toggle_step(s['id'], step_done)
                            st.rerun()
                    with scol2:
                        style = "text-decoration:line-through;opacity:.4" if s['done'] else "opacity:.85"
                        st.markdown(
                            f'<span style="font-size:13px;{style}">{s["content"]}</span>',
                            unsafe_allow_html=True
                        )
                # Re-plan button
                st.markdown("---")
                replan_col, _ = st.columns([1, 2])
                with replan_col:
                    if st.button("🤖 Neu planen", key=f"{pfx}_replan_{eid}", use_container_width=True):
                        st.session_state[f"replan_{eid}"] = True
                        st.rerun()

            if st.session_state.get(f"replan_{eid}"):
                api_k = get_setting('nvidia_api_key', '')
                if api_k:
                    with st.spinner("KI plant Schritte neu..."):
                        try:
                            from openai import OpenAI as _OAI
                            _cl = _OAI(base_url=NVIDIA_BASE_URL, api_key=api_k)
                            rr  = _cl.chat.completions.create(
                                model=KIMI_MODEL,
                                messages=[{
                                    "role": "system",
                                    "content": "Du zerlegst eine Aufgabe in 3-6 Mikro-Schritte (je 2-8 min). Antworte nur mit JSON."
                                }, {
                                    "role": "user",
                                    "content": f'Aufgabe: "{content}"\nErstelle 3-6 konkrete Mikro-Schritte.\nJSON: {{"steps": ["Schritt 1", "Schritt 2", ...]}}'
                                }],
                                max_tokens=400, stream=False
                            )
                            raw2 = rr.choices[0].message.content.strip()
                            if raw2.startswith("```"):
                                raw2 = raw2.split("```")[1]
                                if raw2.startswith("json"):
                                    raw2 = raw2[4:]
                            new_steps = json.loads(raw2).get('steps', [])
                            if new_steps:
                                save_task_steps(eid, new_steps)
                        except Exception:
                            pass
                    st.session_state.pop(f"replan_{eid}", None)
                    st.rerun()
                else:
                    st.warning("Kein API-Key — im KI Coach hinterlegen.")

    open_hl    = sum(1 for r in highlights if not r[9])
    open_todos = sum(1 for r in brains if not r[9])

    tab_hl, tab_todo = st.tabs([
        f"⭐ Highlight ({open_hl} offen)",
        f"📝 To-Do Liste ({open_todos} offen)"
    ])

    # ── TAB 1: DAILY HIGHLIGHT ───────────────────────────────────────
    with tab_hl:
        if highlights:
            for r in highlights:
                render_row(r, "fok-hl", "hl", show_category_controls=False)
        else:
            st.info("Noch kein Highlight — geh zu **Planen** und wähle deine wichtigste Aufgabe.")
            if st.button("Zum Planen →", key="fok_to_plan"):
                st.session_state.page = "Planen"
                st.rerun()

    # ── TAB 2: TO-DO LISTE ───────────────────────────────────────────
    with tab_todo:
        if st.button("➕ Aufgabe hinzufügen", key="fok_quick_toggle"):
            st.session_state['fok_show_add'] = not st.session_state.get('fok_show_add', False)
            st.rerun()

        if st.session_state.get('fok_show_add'):
            with st.form("fok_quick_add"):
                qa1, qa2, qa3 = st.columns([3, 1, 1])
                with qa1:
                    new_task = st.text_input("Aufgabe", label_visibility="collapsed",
                                              placeholder="Aufgabe eingeben...")
                with qa2:
                    cat_opts = ["— keine —"] + [f"{c['icon']} {c['name']}" for c in categories]
                    qa_cat = st.selectbox("Kategorie", cat_opts, label_visibility="collapsed")
                with qa3:
                    qa_micro = st.text_input("⚡ Starter", label_visibility="collapsed",
                                              placeholder="2-min Starter...")
                if st.form_submit_button("✓ Hinzufügen", use_container_width=True):
                    if new_task.strip():
                        new_id = add_entry("brain", new_task.strip(),
                                           estimate=predict_duration("brain"))
                        if qa_cat != "— keine —":
                            chosen_cat = next((c for c in categories
                                               if f"{c['icon']} {c['name']}" == qa_cat), None)
                            if chosen_cat and new_id:
                                set_entry_category(new_id, chosen_cat['id'])
                        if qa_micro.strip() and new_id:
                            _set_micro(new_id, qa_micro.strip())
                        st.session_state['fok_show_add'] = False
                        st.rerun()

        if brains:
            used_cat_ids = {r[15] for r in brains if r[15]}
            active_cats  = [c for c in categories if c['id'] in used_cat_ids]
            if active_cats:
                filter_opts = ["Alle"] + [f"{c['icon']} {c['name']}" for c in active_cats]
                sel_filter = st.radio("", filter_opts, horizontal=True, key="todo_filter_radio")
                if sel_filter != "Alle":
                    cf = next((c for c in active_cats if f"{c['icon']} {c['name']}" == sel_filter), None)
                    visible_brains = [r for r in brains if r[15] == (cf['id'] if cf else None)]
                else:
                    visible_brains = brains
            else:
                visible_brains = brains

            open_tasks = [r for r in visible_brains if not r[9]]
            done_tasks = [r for r in visible_brains if r[9]]

            for r in open_tasks:
                render_row(r, "fok-br", "br")

            if done_tasks:
                with st.expander(f"✅ Erledigt ({len(done_tasks)})"):
                    for r in done_tasks:
                        render_row(r, "fok-br fok-done", "brd")
        else:
            st.info("Noch keine Aufgaben — füge sie über Brain Dump in Planen oder ➕ hinzu.")


def render_alle_eintraege_page():
    st.markdown(URGENCY_CSS, unsafe_allow_html=True)
    st.title("Aufgaben-Kalender")

    all_rows = get_all_entries()
    if not all_rows:
        st.info("Noch keine Einträge — starte mit dem Tag planen.")
        return

    today      = date.today()
    categories = get_categories()
    cat_map    = {c['id']: c for c in categories}

    # ── Controls ────────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns([1, 1, 1])
    with fc1:
        type_filter = st.selectbox("Typ", ["Alle", "Highlight", "To-Do"], key="ae_type",
                                   label_visibility="collapsed")
    with fc2:
        range_filter = st.selectbox("Zeitraum", ["Nächste 14 Tage", "Nächste 30 Tage",
                                                   "Vergangene 7 Tage", "Alles"], key="ae_range",
                                    label_visibility="collapsed")
    with fc3:
        show_done = st.toggle("Erledigte zeigen", value=False, key="ae_show_done")

    # Build date range
    if range_filter == "Nächste 14 Tage":
        date_from = today
        date_to   = today + timedelta(days=14)
    elif range_filter == "Nächste 30 Tage":
        date_from = today
        date_to   = today + timedelta(days=30)
    elif range_filter == "Vergangene 7 Tage":
        date_from = today - timedelta(days=7)
        date_to   = today
    else:
        date_from = date(2020, 1, 1)
        date_to   = today + timedelta(days=365)

    # Filter
    def _passes(r):
        if not show_done and r[9]:
            return False
        try:
            d = date.fromisoformat(r[8])
        except Exception:
            return False
        if not (date_from <= d <= date_to):
            return False
        if type_filter == "Highlight" and r[1] != "highlight":
            return False
        if type_filter == "To-Do" and r[1] not in ("brain", "micro"):
            return False
        return True

    filtered = [r for r in all_rows if _passes(r)]

    # Group by date
    from collections import defaultdict as _dd
    by_date = _dd(list)
    for r in filtered:
        by_date[r[8]].append(r)

    # Stats bar
    open_count = sum(1 for r in filtered if not r[9])
    done_count = sum(1 for r in filtered if r[9])
    days_shown = len(by_date)
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Tage", days_shown)
    sc2.metric("Offen", open_count)
    sc3.metric("Erledigt", done_count)
    sc4.metric("Gesamt", len(filtered))
    st.markdown("---")

    if not by_date:
        st.info("Keine offenen Aufgaben im gewählten Zeitraum.")
        return

    TYPE_ICONS = {"highlight": "⭐", "brain": "📋", "micro": "⚡"}
    TYPE_COLORS = {"highlight": "#ffd700", "brain": "#00d4ff", "micro": "#a29bfe"}

    for day_str in sorted(by_date.keys()):
        day_rows = by_date[day_str]
        try:
            d = date.fromisoformat(day_str)
        except Exception:
            continue

        open_n = sum(1 for r in day_rows if not r[9])
        done_n = sum(1 for r in day_rows if r[9])
        pct    = done_n / len(day_rows) if day_rows else 0
        bar_w  = int(pct * 100)

        # Day label styling
        is_today    = d == today
        is_tomorrow = d == today + timedelta(days=1)
        is_past     = d < today
        if is_today:
            day_color = "#00d4ff"
            day_badge = '<span style="background:#00d4ff22;color:#00d4ff;font-size:10px;font-weight:700;padding:2px 8px;border-radius:6px;margin-left:8px">HEUTE</span>'
        elif is_tomorrow:
            day_color = "#a29bfe"
            day_badge = '<span style="background:#a29bfe22;color:#a29bfe;font-size:10px;font-weight:700;padding:2px 8px;border-radius:6px;margin-left:8px">MORGEN</span>'
        elif is_past:
            day_color = "rgba(255,255,255,0.2)"
            day_badge = ""
        else:
            days_from_today = (d - today).days
            day_color = "#636e72"
            day_badge = f'<span style="font-size:10px;color:rgba(255,255,255,.3);margin-left:8px">in {days_from_today}d</span>'

        wday = WOCHENTAGE[d.weekday()]
        month = MONATE[d.month - 1]

        # Day header
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;margin:20px 0 8px 0">'
            f'<div style="background:{day_color}22;border:1px solid {day_color}44;border-radius:10px;'
            f'padding:8px 14px;min-width:72px;text-align:center">'
            f'<div style="font-size:22px;font-weight:900;color:{day_color};line-height:1">{d.day}</div>'
            f'<div style="font-size:9px;font-weight:700;letter-spacing:1px;color:{day_color};opacity:.7">{wday[:2].upper()}</div>'
            f'</div>'
            f'<div style="flex:1">'
            f'<div style="font-size:13px;font-weight:600;color:rgba(255,255,255,.7)">{wday}, {d.day}. {month}{day_badge}</div>'
            f'<div style="margin-top:5px;background:rgba(255,255,255,.07);border-radius:4px;height:4px">'
            f'<div style="background:linear-gradient(90deg,{day_color},{day_color}99);width:{bar_w}%;height:4px;border-radius:4px"></div>'
            f'</div>'
            f'<div style="font-size:10px;color:rgba(255,255,255,.3);margin-top:3px">{done_n}/{len(day_rows)} erledigt</div>'
            f'</div></div>',
            unsafe_allow_html=True
        )

        # Task cards for this day
        open_rows = [r for r in day_rows if not r[9]]
        done_rows = [r for r in day_rows if r[9]]

        for r in open_rows:
            eid, etype, content, tags, priority, estimate, points, created_at, entry_date, \
                done, completed_at, elapsed_seconds, started_at, deadline, micro_action, category_id = r
            cat      = cat_map.get(category_id)
            t_color  = TYPE_COLORS.get(etype, "#636e72")
            t_icon   = TYPE_ICONS.get(etype, "•")
            urg_level, urg_days, urg_label, _ = get_urgency(deadline)
            cat_html = (f'<span style="background:{cat["color"]}22;color:{cat["color"]};'
                        f'font-size:10px;font-weight:700;padding:1px 7px;border-radius:6px;'
                        f'border:1px solid {cat["color"]}44;margin-left:4px">{cat["icon"]} {cat["name"]}</span>'
                        if cat else "")
            urg_html = (f'<span style="font-size:10px;color:#e74c3c;font-weight:700;margin-left:6px">⚠ {urg_label}</span>'
                        if urg_label else "")
            micro_html = (f'<div style="font-size:11px;color:#00ff88;margin-top:3px">⚡ {micro_action}</div>'
                          if micro_action else "")

            st.markdown(
                f'<div style="display:flex;align-items:flex-start;gap:10px;'
                f'padding:10px 14px;margin:3px 0;'
                f'background:rgba(255,255,255,0.03);border-radius:10px;'
                f'border-left:3px solid {t_color}">'
                f'<span style="font-size:16px;margin-top:1px">{t_icon}</span>'
                f'<div style="flex:1">'
                f'<div style="font-size:13px;font-weight:600;color:rgba(255,255,255,.9)">{content}'
                f'{cat_html}{urg_html}</div>'
                f'{micro_html}'
                f'{"<div style=\'font-size:10px;color:rgba(255,255,255,.3);margin-top:2px\'>⏱️ " + str(estimate) + " min</div>" if estimate else ""}'
                f'</div></div>',
                unsafe_allow_html=True
            )
            cb, bstart, _ = st.columns([0.06, 0.14, 0.80])
            with cb:
                if st.checkbox("", value=False, key=f"ae_chk_{eid}", label_visibility="collapsed"):
                    elapsed = 0
                    if started_at:
                        try:
                            sa = datetime.fromisoformat(started_at)
                            elapsed = int((datetime.utcnow() - sa).total_seconds())
                        except Exception:
                            pass
                    toggle_done(eid, True, elapsed_seconds=elapsed,
                                points=compute_points(elapsed, estimate))
                    st.rerun()
            with bstart:
                if st.button("Stop & ✓" if started_at else "▶ Start",
                             key=f"ae_ss_{eid}", use_container_width=True):
                    if started_at:
                        elapsed = 0
                        try:
                            sa = datetime.fromisoformat(started_at)
                            elapsed = int((datetime.utcnow() - sa).total_seconds())
                        except Exception:
                            pass
                        toggle_done(eid, True, elapsed_seconds=elapsed,
                                    points=compute_points(elapsed, estimate))
                    else:
                        start_task(eid)
                    st.rerun()

        if done_rows and show_done:
            for r in done_rows:
                eid, etype, content = r[0], r[1], r[2]
                t_icon = TYPE_ICONS.get(etype, "•")
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px;padding:6px 14px;'
                    f'margin:2px 0;opacity:.28;text-decoration:line-through;'
                    f'border-radius:8px">'
                    f'<span style="font-size:14px">{t_icon}</span>'
                    f'<span style="font-size:12px">{content}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )


def _render_entry_card(r):
    eid, etype, content, tags, priority, estimate, points, created_at, entry_date, done, completed_at, elapsed_seconds, started_at, deadline, micro_action, category_id = r
    urg_level, urg_days, urg_label, urg_class = get_urgency(deadline)

    card_cls = (urg_class + " urg-done") if done else urg_class
    type_label = TYPE_LABELS.get(etype, etype)
    dl_badge = f'<span class="dl-badge">{urg_label}</span>' if urg_label else ""
    done_badge = '<span class="dl-badge" style="color:#4ade80">✅ Erledigt</span>' if done else ""
    micro_html = (f'<br><span style="font-size:11px;color:#00ff88;opacity:.85">⚡ Starten mit: <em>{micro_action}</em></span>'
                  if micro_action and not done else "")

    st.markdown(
        f'<div class="{card_cls}">'
        f'<span style="font-size:12px;opacity:.6;text-transform:uppercase;letter-spacing:.5px">'
        f'{entry_date} · {type_label}</span>{dl_badge}{done_badge}<br>'
        f'<strong style="font-size:16px">{content}</strong>'
        + micro_html
        + (f'<br><small style="opacity:.55">🏷️ {tags}</small>' if tags else "")
        + (f'<br><small style="opacity:.55">⏱️ ~{estimate} min</small>' if estimate else "")
        + (f'<br><small style="opacity:.55">⭐ {points} Punkte</small>' if done and points else "")
        + '</div>', unsafe_allow_html=True
    )

    if not done:
        c1, c2, c3, _ = st.columns([0.12, 0.18, 0.18, 0.52])
        with c1:
            if st.checkbox("✓", value=False, key=f"ae_chk_{eid}", label_visibility="collapsed"):
                elapsed = 0
                if started_at:
                    try:
                        sa = datetime.fromisoformat(started_at)
                        elapsed = int((datetime.utcnow() - sa).total_seconds())
                    except Exception:
                        pass
                toggle_done(eid, True, elapsed_seconds=elapsed,
                            points=compute_points(elapsed, estimate))
                st.rerun()
        with c2:
            btn_label = "Stop & ✓" if started_at else "Start"
            if st.button(btn_label, key=f"ae_startstop_{eid}"):
                if started_at:
                    elapsed = 0
                    try:
                        sa = datetime.fromisoformat(started_at)
                        elapsed = int((datetime.utcnow() - sa).total_seconds())
                    except Exception:
                        pass
                    toggle_done(eid, True, elapsed_seconds=elapsed,
                                points=compute_points(elapsed, estimate))
                else:
                    start_task(eid)
                st.rerun()
    else:
        c1, _ = st.columns([0.12, 0.88])
        with c1:
            if st.checkbox("✓", value=True, key=f"ae_chk_{eid}", label_visibility="collapsed"):
                pass
            else:
                toggle_done(eid, False, elapsed_seconds=0)
                st.rerun()


def render_projekte_page():
    st.markdown(URGENCY_CSS, unsafe_allow_html=True)

    if st.session_state.get('selected_project'):
        _render_project_detail(st.session_state.selected_project)
        return

    st.title("Projekte")
    st.caption("Große Ziele — automatisch auf tägliche Aufgaben runtergebrochen.")

    with st.expander("➕ Neues Projekt erstellen", expanded=False):
        with st.form("new_project_form"):
            name = st.text_input("Projektname", placeholder="z.B. Video Kurs Trading & Risikomanagement")
            description = st.text_area("Beschreibung (optional)", height=60)
            col1, col2, col3 = st.columns(3)
            with col1:
                deadline = st.date_input("Deadline", value=date.today() + timedelta(days=30))
            with col2:
                daily_minutes = st.number_input("Arbeitszeit/Tag (Min)", min_value=15, step=15, value=60)
            with col3:
                color = st.color_picker("Projektfarbe", value="#60a5fa")
            if st.form_submit_button("Projekt anlegen", use_container_width=True):
                if name.strip():
                    pid = add_project(name.strip(), description.strip(), deadline.isoformat(), color, daily_minutes)
                    st.session_state.selected_project = pid
                    st.rerun()

    st.markdown("---")
    projects = get_projects()
    if not projects:
        st.info("Noch keine Projekte — erstelle dein erstes Projekt oben.")
        return

    for proj in projects:
        pid, name, description, deadline, color, active, created_at, daily_minutes = proj
        tasks = get_project_tasks(pid)
        total = len(tasks)
        done_c = sum(1 for t in tasks if t[5])
        pct = done_c / total if total > 0 else 0
        next_task = next((t for t in tasks if not t[5]), None)
        _, _, urg_label, _ = get_urgency(deadline)

        st.markdown(
            f'<div style="border-left:5px solid {color};background:rgba(0,0,0,0.15);'
            f'border-radius:10px;padding:16px 20px;margin-bottom:4px">'
            f'<strong style="font-size:18px">{name}</strong>'
            + (f'<span class="dl-badge">{urg_label}</span>' if urg_label else
               f'<span class="dl-badge">📅 {deadline}</span>' if deadline else "")
            + f'<span class="dl-badge">⏱️ {daily_minutes} min/Tag</span>'
            + f'<br><small style="opacity:.65">{done_c}/{total} Aufgaben · {int(pct*100)}% erledigt</small>'
            + (f'<br><small style="opacity:.65">➡️ Als nächstes: <em>{next_task[2]}</em></small>' if next_task else
               '<br><small style="color:#4ade80">✅ Alle Aufgaben erledigt!</small>' if total > 0 else "")
            + '</div>', unsafe_allow_html=True
        )
        st.progress(pct)
        c1, c2, c3, _ = st.columns([0.16, 0.18, 0.12, 0.54])
        with c1:
            if st.button("Öffnen →", key=f"proj_open_{pid}", use_container_width=True):
                st.session_state.selected_project = pid
                st.rerun()
        with c2:
            if st.button("🔄 Einplanen", key=f"proj_sched_{pid}", use_container_width=True):
                schedule_project_tasks(pid)
                st.success("Neu eingeplant!")
                st.rerun()
        with c3:
            if st.button("🗑️", key=f"proj_del_{pid}"):
                delete_project(pid)
                st.rerun()
        st.markdown("")


def _activity_markov_chain():
    """Baut eine 2-Zustands-Markov-Kette (aktiv/inaktiv) aus der kompletten Tagesverlauf-Historie.
    'aktiv' = an diesem Tag wurde mindestens eine Aufgabe (egal welches Projekt) erledigt."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT entry_date, COALESCE(SUM(done),0) FROM entries "
        "WHERE entry_date IS NOT NULL AND entry_date != '' GROUP BY entry_date ORDER BY entry_date"
    ).fetchall()
    conn.close()
    if len(rows) < 2:
        return None

    day_done = {}
    for d, done_sum in rows:
        try:
            date.fromisoformat(d)
        except (ValueError, TypeError):
            continue
        day_done[d] = 1 if (done_sum or 0) > 0 else 0
    if len(day_done) < 2:
        return None

    start = date.fromisoformat(min(day_done.keys()))
    end = date.fromisoformat(max(day_done.keys()))
    series = []
    cur = start
    while cur <= end:
        series.append(day_done.get(cur.isoformat(), 0))
        cur += timedelta(days=1)

    trans = {(0, 0): 0, (0, 1): 0, (1, 0): 0, (1, 1): 0}
    for i in range(len(series) - 1):
        trans[(series[i], series[i + 1])] += 1

    n0 = trans[(0, 0)] + trans[(0, 1)]
    n1 = trans[(1, 0)] + trans[(1, 1)]
    p_inactive_after_inactive = trans[(0, 0)] / n0 if n0 > 0 else 0.6
    p_inactive_after_active = trans[(1, 0)] / n1 if n1 > 0 else 0.25

    streak_state = series[-1]
    streak_len = 1
    for v in reversed(series[:-1]):
        if v == streak_state:
            streak_len += 1
        else:
            break

    return {
        'p_inactive_after_inactive': p_inactive_after_inactive,
        'p_inactive_after_active': p_inactive_after_active,
        'p_active_after_inactive': 1 - p_inactive_after_inactive,
        'p_active_after_active': 1 - p_inactive_after_active,
        'today_state': series[-1],
        'streak_state': streak_state,
        'streak_len': streak_len,
        'series': series,
        'dates': [(start + timedelta(days=i)).isoformat() for i in range(len(series))],
        'sample_size': n0 + n1,
    }


def _project_velocity_samples(pid, fallback_minutes=30):
    """Minuten erledigte Projektarbeit pro Tag, an dem an diesem Projekt etwas erledigt wurde."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT completed_at, estimate_minutes FROM project_tasks "
        "WHERE project_id=? AND done=1 AND completed_at IS NOT NULL", (pid,)
    ).fetchall()
    conn.close()
    by_day = {}
    for completed_at, est in rows:
        if not completed_at:
            continue
        d = completed_at[:10]
        by_day[d] = by_day.get(d, 0) + (est or fallback_minutes)
    samples = list(by_day.values())
    return samples if samples else [fallback_minutes]


def _simulate_project_completion(remaining_mins, days_left, markov, velocity_samples,
                                   force_today_state=None, n_sims=3000):
    """Monte-Carlo-Simulation: wie wahrscheinlich ist es, das Restpensum bis zur Deadline
    zu schaffen, basierend auf der empirischen Markov-Kette für Aktiv/Inaktiv-Tage und
    der tatsächlichen Velocity-Verteilung dieses Projekts (Bootstrap)."""
    if remaining_mins <= 0:
        return 1.0
    if days_left is None or days_left < 0:
        return 0.0

    successes = 0
    for _ in range(n_sims):
        acc = 0
        state = force_today_state if force_today_state is not None else markov['today_state']
        for day in range(days_left + 1):
            if day > 0:
                p_inactive = (markov['p_inactive_after_active'] if state == 1
                              else markov['p_inactive_after_inactive'])
                state = 0 if random.random() < p_inactive else 1
            if state == 1:
                acc += random.choice(velocity_samples)
            if acc >= remaining_mins:
                successes += 1
                break
    return successes / n_sims


def _build_forecast_gauge(pct, label, sublabel):
    """Kompakter SVG-Ring (ähnlich Tagesfokus-Hero) für die Erfolgswahrscheinlichkeit."""
    pct = max(0, min(100, pct))
    if pct < 35:
        col, glow = "#e74c3c", "rgba(231,76,60,0.45)"
    elif pct < 65:
        col, glow = "#f39c12", "rgba(243,156,18,0.45)"
    else:
        col, glow = "#2ecc71", "rgba(46,204,113,0.45)"
    r = 70
    circumference = 2 * math.pi * r
    offset = circumference * (1 - pct / 100)
    return f"""<!DOCTYPE html>
<html><head><style>
  html,body{{margin:0;padding:0;background:#0e1117;overflow:hidden;
             font-family:system-ui,-apple-system,sans-serif}}
  .wrap{{display:flex;align-items:center;justify-content:center;height:190px}}
  svg{{transform:rotate(-90deg)}}
  .ring-bg{{fill:none;stroke:rgba(255,255,255,0.08);stroke-width:12}}
  .ring-fg{{fill:none;stroke:{col};stroke-width:12;stroke-linecap:round;
            stroke-dasharray:{circumference:.2f};
            stroke-dashoffset:{circumference:.2f};
            filter:drop-shadow(0 0 8px {glow});
            animation:fillin 1.4s cubic-bezier(.22,.9,.34,1) forwards}}
  @keyframes fillin{{to{{stroke-dashoffset:{offset:.2f}}}}}
  .center{{position:absolute;text-align:center}}
  .pctnum{{font-size:34px;font-weight:900;color:{col}}}
  .lbl{{font-size:10px;color:rgba(255,255,255,0.45);letter-spacing:1px;margin-top:2px}}
  .sub{{font-size:9px;color:rgba(255,255,255,0.3);margin-top:6px}}
</style></head><body>
<div class="wrap" style="position:relative">
  <svg width="170" height="170" viewBox="0 0 170 170">
    <circle class="ring-bg" cx="85" cy="85" r="{r}"/>
    <circle class="ring-fg" cx="85" cy="85" r="{r}"/>
  </svg>
  <div class="center">
    <div class="pctnum">{pct}%</div>
    <div class="lbl">{label}</div>
    <div class="sub">{sublabel}</div>
  </div>
</div>
</body></html>"""


def _render_project_forecast(pid, tasks, deadline, daily_minutes):
    undone = [t for t in tasks if not t[5]]
    remaining_mins = sum(t[3] or 0 for t in undone)

    if not remaining_mins:
        st.success("✅ Alle Aufgaben erledigt — keine Prognose nötig.")
        return
    if not deadline:
        st.info("📅 Setze eine Deadline in den Projekteinstellungen, um eine Prognose zu sehen.")
        return

    today = date.today()
    try:
        days_left = (date.fromisoformat(deadline) - today).days
    except Exception:
        st.info("Ungültige Deadline.")
        return

    markov = _activity_markov_chain()
    if markov is None or markov['sample_size'] < 5:
        st.info("📈 Noch nicht genug Verlaufsdaten für eine zuverlässige Prognose — "
                "sammle ein paar Tage Aktivität, dann rechnet Kaizen mit echten Mustern statt Annahmen.")
        return

    velocity_samples = _project_velocity_samples(pid, fallback_minutes=daily_minutes or 30)

    p_baseline = _simulate_project_completion(remaining_mins, days_left, markov, velocity_samples)
    p_continue = _simulate_project_completion(remaining_mins, days_left, markov, velocity_samples,
                                                force_today_state=1)
    p_skip = _simulate_project_completion(remaining_mins, days_left, markov, velocity_samples,
                                            force_today_state=0)

    st.markdown("##### 🔮 Erfolgswahrscheinlichkeit")
    gc1, gc2 = st.columns([1, 1.4])
    with gc1:
        pct = int(round(p_baseline * 100))
        sub = f"{remaining_mins} min offen · {days_left} Tage" if days_left >= 0 else "Deadline überschritten"
        components.html(_build_forecast_gauge(pct, "bei aktuellem Tempo", sub), height=190, scrolling=False)

    with gc2:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        delta_pp = (p_continue - p_skip) * 100
        st.markdown(f"""
<div style="display:flex;gap:10px">
  <div style="flex:1;background:rgba(46,204,113,0.08);border:1px solid rgba(46,204,113,0.25);
              border-radius:12px;padding:12px 14px">
    <div style="font-size:9px;color:#2ecc71;letter-spacing:1.5px;text-transform:uppercase">
      🔥 Pfad: Heute aktiv</div>
    <div style="font-size:26px;font-weight:900;color:#2ecc71;margin-top:4px">
      {int(round(p_continue*100))}%</div>
    <div style="font-size:10px;color:rgba(255,255,255,0.4);margin-top:2px">
      Erfolgschance wenn du heute etwas schaffst</div>
  </div>
  <div style="flex:1;background:rgba(231,76,60,0.08);border:1px solid rgba(231,76,60,0.25);
              border-radius:12px;padding:12px 14px">
    <div style="font-size:9px;color:#e74c3c;letter-spacing:1.5px;text-transform:uppercase">
      🧊 Pfad: Heute aussetzen</div>
    <div style="font-size:26px;font-weight:900;color:#e74c3c;margin-top:4px">
      {int(round(p_skip*100))}%</div>
    <div style="font-size:10px;color:rgba(255,255,255,0.4);margin-top:2px">
      Erfolgschance wenn heute 0 Aufgaben passieren</div>
  </div>
</div>
<div style="margin-top:8px;font-size:11px;color:rgba(255,255,255,0.5)">
  Differenz: <strong style="color:#00d4ff">{delta_pp:.0f} Prozentpunkte</strong> —
  so viel kostet dich ein Nulltag bei diesem Projekt, statistisch gesehen.</div>
""", unsafe_allow_html=True)

    # ── Spiral-Risk ──────────────────────────────────────────
    p_spiral = markov['p_inactive_after_inactive'] * 100
    p_bounce = markov['p_inactive_after_active'] * 100
    streak_txt = ("noch keine Aufgabe heute" if markov['today_state'] == 0
                  else "heute schon aktiv")
    spiral_col = "#e74c3c" if p_spiral >= 55 else "#f39c12" if p_spiral >= 35 else "#2ecc71"
    if markov['streak_state'] == 0 and markov['streak_len'] >= 2:
        spiral_note = (f"⚠️ Du bist seit <strong>{markov['streak_len']} Tagen</strong> inaktiv. "
                        f"Historisch bleibst du nach einem inaktiven Tag zu <strong>{p_spiral:.0f}%</strong> "
                        f"auch am nächsten Tag inaktiv — das ist dein Prokrastinations-Muster, "
                        f"keine Vermutung, sondern aus deinen eigenen Daten berechnet.")
    else:
        spiral_note = (f"Nach einem inaktiven Tag bist du historisch zu <strong>{p_spiral:.0f}%</strong> "
                        f"auch am Folgetag inaktiv — nach einem aktiven Tag nur zu "
                        f"<strong>{p_bounce:.0f}%</strong>. Aktiv bleiben senkt dein Rückfallrisiko "
                        f"um <strong>{p_spiral - p_bounce:.0f} Prozentpunkte</strong>.")
    st.markdown(f"""
<div style="background:rgba(255,255,255,0.04);border-left:3px solid {spiral_col};
            border-radius:0 10px 10px 0;padding:12px 16px;margin-top:14px;font-size:12px;
            color:rgba(255,255,255,0.75);line-height:1.6">
  {spiral_note}
</div>""", unsafe_allow_html=True)

    # ── Aktivitäts-Kalender (GitHub-Style Heatmap) ────────────
    series = markov['series'][-84:]
    dates_s = markov['dates'][-84:]
    n_cols = math.ceil(len(series) / 7)
    cells = ""
    for col in range(n_cols):
        for row in range(7):
            idx = col * 7 + row
            if idx >= len(series):
                continue
            active = series[idx]
            d_obj = date.fromisoformat(dates_s[idx])
            is_today = d_obj == today
            bg = "#2ecc71" if active else "rgba(255,255,255,0.08)"
            border = "2px solid #00d4ff" if is_today else "1px solid rgba(255,255,255,0.04)"
            cells += (f'<div title="{dates_s[idx]}: {"aktiv" if active else "inaktiv"}" '
                      f'style="width:11px;height:11px;border-radius:3px;background:{bg};'
                      f'border:{border};grid-column:{col+1};grid-row:{row+1}"></div>')
    st.markdown(f"""
<div style="margin-top:16px">
  <div style="font-size:9px;color:rgba(255,255,255,0.35);letter-spacing:1.5px;
              text-transform:uppercase;margin-bottom:8px">📅 Aktivitätsmuster (letzte {len(series)} Tage)</div>
  <div style="display:grid;grid-template-columns:repeat({n_cols},11px);grid-template-rows:repeat(7,11px);
              gap:3px;overflow-x:auto;padding-bottom:4px">
    {cells}
  </div>
  <div style="font-size:9px;color:rgba(255,255,255,0.25);margin-top:6px">
    🟩 aktiver Tag · ⬜ inaktiver Tag · 🔵 Rand = heute
  </div>
</div>""", unsafe_allow_html=True)


def _render_project_detail(project_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, name, description, deadline, color, active, created_at, daily_minutes FROM projects WHERE id=?', (project_id,))
    proj = c.fetchone()
    conn.close()
    if not proj:
        st.session_state.selected_project = None
        st.rerun()
        return

    pid, name, description, deadline, color, active, created_at, daily_minutes = proj

    if st.button("← Alle Projekte", key="proj_back"):
        st.session_state.selected_project = None
        st.rerun()

    tasks = get_project_tasks(pid)
    total = len(tasks)
    done_count = sum(1 for t in tasks if t[5])
    total_mins = sum(t[3] or 0 for t in tasks)
    done_mins  = sum(t[3] or 0 for t in tasks if t[5])
    pct = done_count / total if total > 0 else 0

    try:
        days_left = (date.fromisoformat(deadline) - date.today()).days
    except Exception:
        days_left = None

    st.markdown(f'<h2 style="color:{color};margin-bottom:4px">{name}</h2>', unsafe_allow_html=True)
    if description:
        st.caption(description)

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Aufgaben", f"{done_count} / {total}")
    mc2.metric("Fortschritt", f"{int(pct*100)} %")
    mc3.metric("Zeit erledigt", f"{done_mins} min")
    if days_left is not None:
        mc4.metric("Tage bis Deadline", days_left)

    st.progress(pct)

    if days_left is not None:
        undone = [t for t in tasks if not t[5]]
        if undone:
            remaining_mins = sum(t[3] or 0 for t in undone)
            if days_left > 0:
                needed = remaining_mins / days_left
                if days_left < 0:
                    st.error(f"⚠️ Deadline überschritten! Noch {remaining_mins} min Arbeit offen.")
                elif days_left <= 3:
                    st.warning(f"⏰ Nur noch {days_left} Tage! Ca. {int(needed)} min/Tag nötig.")
                else:
                    st.info(f"📊 {remaining_mins} min offen · ca. {int(needed)} min/Tag nötig · {daily_minutes} min/Tag geplant")

    st.markdown("---")

    col1, col2, _ = st.columns([0.28, 0.28, 0.44])
    with col1:
        if st.button("🔄 Aufgaben neu einplanen", use_container_width=True):
            schedule_project_tasks(pid)
            st.success("Neu eingeplant!")
            st.rerun()
    with col2:
        if st.button("⚙️ Projekteinstellungen", use_container_width=True, key="proj_settings_btn"):
            st.session_state[f'proj_settings_{pid}'] = not st.session_state.get(f'proj_settings_{pid}', False)
            st.rerun()

    if st.session_state.get(f'proj_settings_{pid}'):
        with st.form("edit_project_form"):
            new_name = st.text_input("Name", value=name)
            new_desc = st.text_area("Beschreibung", value=description or "", height=60)
            c1, c2, c3 = st.columns(3)
            with c1:
                new_deadline = st.date_input("Deadline", value=date.fromisoformat(deadline) if deadline else date.today())
            with c2:
                new_daily = st.number_input("Min/Tag", min_value=15, step=15, value=daily_minutes or 60)
            with c3:
                new_color = st.color_picker("Farbe", value=color or "#60a5fa")
            if st.form_submit_button("Speichern"):
                conn2 = sqlite3.connect(DB_PATH)
                c2 = conn2.cursor()
                c2.execute('UPDATE projects SET name=?, description=?, deadline=?, daily_minutes=?, color=? WHERE id=?',
                           (new_name, new_desc, new_deadline.isoformat(), new_daily, new_color, pid))
                conn2.commit()
                conn2.close()
                st.session_state[f'proj_settings_{pid}'] = False
                st.rerun()

    # Add task form
    with st.expander("➕ Aufgabe hinzufügen"):
        with st.form("add_task_form"):
            task_content = st.text_input("Aufgabe", placeholder="Was muss gemacht werden?")
            col1, col2 = st.columns(2)
            with col1:
                task_estimate = st.number_input("Minuten", min_value=5, step=5, value=30)
            with col2:
                task_priority = st.slider("Priorität", min_value=0, max_value=10, value=5)
            if st.form_submit_button("Aufgabe hinzufügen", use_container_width=True):
                if task_content.strip():
                    add_project_task(pid, task_content.strip(), task_estimate, task_priority)
                    schedule_project_tasks(pid)
                    st.rerun()

    st.markdown("---")

    # ── Task list ─────────────────────────────────────────────────────────────
    undone_tasks = [t for t in tasks if not t[5]]
    done_tasks   = [t for t in tasks if t[5]]
    today_str    = date.today().isoformat()

    PRESET_COLORS = [
        ("Kein", ""),
        ("🟡 Gelb",  "#ffd700"),
        ("🔴 Rot",   "#e74c3c"),
        ("🟢 Grün",  "#2ecc71"),
        ("🔵 Blau",  "#3498db"),
        ("🟣 Lila",  "#9b59b6"),
        ("🟠 Orange","#f39c12"),
        ("⚪ Weiß",  "#ecf0f1"),
    ]

    if undone_tasks:
        st.subheader(f"📋 Offen ({len(undone_tasks)})")
        for i, t in enumerate(undone_tasks):
            task_id, _, content, estimate, priority, done, completed_at, scheduled_date, order_idx, notes, hl_color = t
            is_today   = scheduled_date == today_str
            border_c   = hl_color if hl_color else ("#ffd700" if is_today else color)
            card_bg    = f"{hl_color}12" if hl_color else ("rgba(255,215,0,0.06)" if is_today else "rgba(255,255,255,0.03)")
            edit_open  = st.session_state.get(f"pt_edit_{task_id}", False)

            notes_preview = (
                f'<div style="font-size:11px;color:rgba(255,255,255,.45);margin-top:5px;'
                f'white-space:pre-wrap;border-left:2px solid rgba(255,255,255,.15);padding-left:8px">'
                f'{notes[:160]}{"…" if len(notes)>160 else ""}</div>'
            ) if notes and not edit_open else ""

            st.markdown(
                f'<div style="border-left:4px solid {border_c};background:{card_bg};'
                f'border-radius:10px;padding:10px 16px;margin-bottom:2px">'
                f'<strong style="font-size:14px">{content}</strong>'
                + (f'<span class="dl-badge" style="color:#ffd700">📅 Heute</span>' if is_today else
                   f'<span class="dl-badge">{scheduled_date}</span>' if scheduled_date else "")
                + (f'<span class="dl-badge">⏱️ {estimate} min</span>' if estimate else "")
                + (f'<span class="dl-badge">★ {priority}</span>' if priority else "")
                + notes_preview + '</div>', unsafe_allow_html=True
            )

            # Action row
            cc, cup, cdn, cedit, cdel = st.columns([0.06, 0.06, 0.06, 0.16, 0.06])
            with cc:
                if st.checkbox("", value=False, key=f"pt_chk_{task_id}", label_visibility="collapsed"):
                    toggle_project_task_done(task_id, True)
                    st.rerun()
            with cup:
                if i > 0 and st.button("↑", key=f"pt_up_{task_id}", use_container_width=True):
                    move_project_task(task_id, -1, pid)
                    st.rerun()
            with cdn:
                if i < len(undone_tasks)-1 and st.button("↓", key=f"pt_dn_{task_id}", use_container_width=True):
                    move_project_task(task_id, 1, pid)
                    st.rerun()
            with cedit:
                edit_lbl = "✕ Schließen" if edit_open else "✏️ Bearbeiten"
                if st.button(edit_lbl, key=f"pt_editbtn_{task_id}", use_container_width=True):
                    st.session_state[f"pt_edit_{task_id}"] = not edit_open
                    st.rerun()
            with cdel:
                if st.button("🗑️", key=f"pt_del_{task_id}", use_container_width=True):
                    delete_project_task(task_id)
                    st.session_state.pop(f"pt_edit_{task_id}", None)
                    st.rerun()

            # Inline full editor
            if edit_open:
                with st.form(f"pt_edit_form_{task_id}"):
                    new_content = st.text_input("Aufgabe", value=content, key=f"pe_cnt_{task_id}")

                    ea, eb, ec = st.columns(3)
                    with ea:
                        new_est = st.number_input("⏱️ Minuten", min_value=1, step=5,
                                                   value=int(estimate or 30), key=f"pe_est_{task_id}")
                    with eb:
                        new_prio = st.slider("★ Priorität", 0, 10,
                                             value=int(priority or 5), key=f"pe_prio_{task_id}")
                    with ec:
                        try:
                            sd_val = date.fromisoformat(scheduled_date) if scheduled_date else date.today()
                        except Exception:
                            sd_val = date.today()
                        new_date = st.date_input("📅 Datum", value=sd_val, key=f"pe_date_{task_id}")

                    # Color picker row
                    st.markdown("**🎨 Hervorhebungsfarbe**")
                    color_cols = st.columns(len(PRESET_COLORS))
                    selected_color = hl_color  # will be overridden by radio
                    color_labels = [p[0] for p in PRESET_COLORS]
                    cur_color_idx = next((i for i, p in enumerate(PRESET_COLORS) if p[1] == hl_color), 0)
                    chosen_label = st.radio("Farbe", color_labels, index=cur_color_idx,
                                            horizontal=True, label_visibility="collapsed",
                                            key=f"pe_color_{task_id}")
                    chosen_color = next((p[1] for p in PRESET_COLORS if p[0] == chosen_label), "")
                    # Custom color picker
                    use_custom = st.checkbox("Eigene Farbe", key=f"pe_custom_chk_{task_id}")
                    if use_custom:
                        chosen_color = st.color_picker("Farbe wählen",
                                                        value=hl_color if hl_color else "#ffffff",
                                                        key=f"pe_cpick_{task_id}")

                    new_notes = st.text_area("📝 Notizen", value=notes or "", height=120,
                                             placeholder="Gedanken, Links, Zwischenstände, Quellen...",
                                             key=f"pe_notes_{task_id}")

                    fs, fc = st.columns(2)
                    with fs:
                        if st.form_submit_button("💾 Speichern", use_container_width=True):
                            update_project_task(task_id, new_content.strip(), new_est, new_prio,
                                                new_notes.strip(), chosen_color,
                                                new_date.isoformat())
                            st.session_state.pop(f"pt_edit_{task_id}", None)
                            st.rerun()
                    with fc:
                        if st.form_submit_button("✕ Abbrechen", use_container_width=True):
                            st.session_state.pop(f"pt_edit_{task_id}", None)
                            st.rerun()

            st.markdown('<div style="margin-bottom:2px"></div>', unsafe_allow_html=True)

    if done_tasks:
        with st.expander(f"✅ Erledigt ({len(done_tasks)})"):
            for t in done_tasks:
                task_id, _, content, estimate, priority, done, completed_at, scheduled_date, order_idx, notes, hl_color = t
                st.markdown(f'<div style="opacity:.4;text-decoration:line-through;padding:4px 0">{content}'
                            + (f' <small>({estimate} min)</small>' if estimate else '') + '</div>',
                            unsafe_allow_html=True)
                c1, _ = st.columns([0.10, 0.90])
                with c1:
                    if not st.checkbox("", value=True, key=f"pt_chk_{task_id}", label_visibility="collapsed"):
                        toggle_project_task_done(task_id, False)
                        st.rerun()

    # ── Visualizations ────────────────────────────────────────────────────────
    if tasks:
        st.markdown("---")
        st.subheader("📊 Zeitplan & Fortschritt")

        tab1, tab2, tab3 = st.tabs(["Gantt-Zeitplan", "Burndown", "🔮 Prognose"])

        with tab1:
            gantt_data = []
            for t in tasks:
                task_id, _, content, estimate, priority, done, completed_at, scheduled_date, _, _, _ = t
                if scheduled_date:
                    try:
                        start_dt = datetime.combine(date.fromisoformat(scheduled_date),
                                                     datetime.min.time())
                        end_dt = start_dt + timedelta(minutes=max(estimate or 30, 15))
                        gantt_data.append({
                            'Aufgabe': (content[:35] + '…') if len(content) > 35 else content,
                            'Start': start_dt.strftime('%Y-%m-%d %H:%M:%S'),
                            'Ende':  end_dt.strftime('%Y-%m-%d %H:%M:%S'),
                            'Status': 'Erledigt' if done else 'Offen',
                        })
                    except Exception:
                        pass
            if gantt_data:
                df_g = pd.DataFrame(gantt_data)
                fig_g = px.timeline(df_g, x_start='Start', x_end='Ende', y='Aufgabe',
                                     color='Status',
                                     color_discrete_map={'Erledigt': '#4ade80', 'Offen': color},
                                     template='plotly_dark')
                fig_g.update_yaxes(autorange="reversed")
                fig_g.add_vline(x=datetime.combine(date.today(), datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S'),
                                 line_dash="dash", line_color="#ffd700",
                                 annotation_text="Heute", annotation_font_color="#ffd700")
                if deadline:
                    fig_g.add_vline(x=datetime.combine(date.fromisoformat(deadline), datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S'),
                                     line_dash="dot", line_color="#ef4444",
                                     annotation_text="Deadline", annotation_font_color="#ef4444")
                st.plotly_chart(fig_g, use_container_width=True)
            else:
                st.info("Plane Aufgaben ein um den Zeitplan zu sehen.")

        with tab2:
            if done_tasks:
                from collections import Counter
                done_dates = [t[6][:10] for t in done_tasks if t[6]]
                if done_dates:
                    counts = Counter(done_dates)
                    df_b = pd.DataFrame(sorted(counts.items()), columns=['Datum', 'Neu_erledigt'])
                    df_b['Kumulativ'] = df_b['Neu_erledigt'].cumsum()

                    fig_b = go.Figure()
                    fig_b.add_trace(go.Scatter(
                        x=df_b['Datum'], y=df_b['Kumulativ'],
                        mode='lines+markers', name='Erledigt',
                        line=dict(color='#4ade80', width=3),
                        fill='tozeroy', fillcolor='rgba(74,222,128,0.08)'
                    ))
                    fig_b.add_hline(y=total, line_dash="dash", line_color="#60a5fa",
                                     annotation_text=f"Gesamt: {total} Aufgaben",
                                     annotation_font_color="#60a5fa")
                    fig_b.update_layout(template='plotly_dark', showlegend=False,
                                         yaxis_title="Aufgaben erledigt")
                    st.plotly_chart(fig_b, use_container_width=True)
            else:
                st.info("Erledige Aufgaben um den Fortschritt zu sehen.")

        with tab3:
            _render_project_forecast(pid, tasks, deadline, daily_minutes)


def render_routinen_page():
    st.markdown(URGENCY_CSS, unsafe_allow_html=True)
    st.title("Routinen")
    st.caption("Aufgaben die sich wiederholen — werden automatisch jeden Tag eingeplant.")

    routines = get_recurring_tasks()

    # ── Neue Routine hinzufügen ──────────────────────────────────────────────
    with st.expander("➕ Neue Routine hinzufügen", expanded=len(routines) == 0):
        with st.form("new_routine_form"):
            content = st.text_input("Aufgabe", placeholder="z.B. Meditation, Journal schreiben...")
            col1, col2 = st.columns(2)
            with col1:
                etype = st.selectbox("Typ", ["micro", "brain", "highlight"],
                                      format_func=lambda x: TYPE_LABELS.get(x, x))
                time_of_day = st.selectbox("Tageszeit",
                                            ["morgen", "abend", "anytime"],
                                            format_func=lambda x: f"{TIME_ICONS[x]} {TIME_LABELS[x]}")
            with col2:
                estimate = st.number_input("Minuten", min_value=0, step=5, value=5)
                tags = st.text_input("Extra-Tags (optional)")

            st.markdown("**Wiederholung**")
            preset = st.radio("Vorlage", list(RECURRENCE_PRESETS.keys()), horizontal=True)
            if preset == "Benutzerdefiniert":
                day_cols = st.columns(7)
                selected_days = []
                for i, (col, abbr) in enumerate(zip(day_cols, DAY_ABBR)):
                    if col.checkbox(abbr, value=True, key=f"day_{i}"):
                        selected_days.append(str(i))
                recurrence = ",".join(selected_days) if selected_days else "0,1,2,3,4,5,6"
            else:
                recurrence = RECURRENCE_PRESETS[preset]

            if st.form_submit_button("Routine speichern", use_container_width=True):
                if content.strip():
                    add_recurring_task(etype, content.strip(), tags, estimate, recurrence, time_of_day)
                    st.rerun()

    st.markdown("---")

    if not routines:
        st.info("Noch keine Routinen — füge deine erste Morgen- oder Abend-Routine hinzu.")
        return

    # ── Routinen anzeigen, gruppiert nach Tageszeit ───────────────────────────
    groups = [("morgen", "🌅 Morgen-Routine"), ("abend", "🌙 Abend-Routine"), ("anytime", "📋 Aufgaben")]
    for g_key, g_label in groups:
        group = [r for r in routines if r[6] == g_key]
        if not group:
            continue
        st.subheader(g_label)
        for rt in group:
            rt_id, etype, content, tags, estimate, recurrence, time_of_day, active, last_generated = rt
            rec_label = format_recurrence(recurrence)
            type_label = TYPE_LABELS.get(etype, etype)

            today_str = date.today().isoformat()
            synced_today = last_generated == today_str

            card_style = (
                "border-left:4px solid #4ade80;background:rgba(74,222,128,0.06);"
                if active else
                "border-left:4px solid #475569;background:rgba(71,85,105,0.04);opacity:.5;"
            )
            st.markdown(
                f'<div style="{card_style}border-radius:8px;padding:12px 16px;margin-bottom:8px">'
                f'<strong>{content}</strong>'
                f'<span class="dl-badge">{rec_label}</span>'
                f'<span class="dl-badge">{type_label}</span>'
                + (f'<span class="dl-badge">⏱️ {estimate} min</span>' if estimate else "")
                + (f'<span class="dl-badge" style="color:#4ade80">✅ heute eingeplant</span>' if synced_today else "")
                + '</div>', unsafe_allow_html=True
            )
            c_tog, c_del, _ = st.columns([0.18, 0.18, 0.64])
            with c_tog:
                new_active = st.toggle("Aktiv", value=bool(active), key=f"rt_tog_{rt_id}")
                if new_active != bool(active):
                    toggle_recurring_active(rt_id, new_active)
                    st.rerun()
            with c_del:
                if st.button("🗑️ Löschen", key=f"rt_del_{rt_id}"):
                    delete_recurring_task(rt_id)
                    st.rerun()

    st.markdown("---")
    st.caption(f"Routinen werden täglich beim App-Start automatisch in den Tagesplan eingeplant.")


def _get_char_body(char_level, class_id, equipped_body):
    if equipped_body == 'godly': return '🌟'
    if equipped_body == 'shadow': return '🦇'
    if equipped_body == 'crown': pass  # handled as overlay
    ci = CLASS_INFO.get(class_id, {})
    bodies = ci.get('bodies', {1: '🧍', 5: '⚔️', 15: '🥷', 25: '🦸', 50: '🌟', 100: '👑'})
    body = '🧍'
    for req_lvl in sorted(bodies.keys()):
        if char_level >= req_lvl:
            body = bodies[req_lvl]
    return body


_CHAR_AURA_COLORS = {
    'blue':'#00d4ff','green':'#00ff88','purple':'#9b59b6','dragon':'#e74c3c',
    'rainbow':'#ff00ff','divine':'#ffd700',
    'ocean_s1':'#006994','star_s1':'#ffd700','dawn_s1':'#ff7f50','cosmic_s1':'#8040ff',
    'rift_s1':'#00ffcc','deep_s1':'#003d66','beyond_s1':'#7000ff',
    'legend_s1':'#ffaa00','absolute_s1':'#ffffff',
    'void_s2':'#4a0080','night_s2':'#191970','shadow_s2':'#444',
    'ember_s3':'#ff6600','hellfire_s3':'#ff0000',
}

_SEASON_BODY_MAP = {
    'crown':'👑','shadow':'🦇','godly':'🌟',
    'rise':'🛡️','guardian':'🗡️','divine_s1':'🌟',
    'ghost':'👻','shade_s2':'🌑',
    'fire_s3':'🔥','demon_s3':'😈',
}


def _build_char_visual(char, level):
    ci = CLASS_INFO.get(char.get('class_id', ''), {})
    class_col = ci.get('color', '#00d4ff')
    eq_aura = char.get('equipped_aura', '') or ''
    glow_col = _CHAR_AURA_COLORS.get(eq_aura, class_col)
    eq_body = char.get('equipped_body', '') or ''
    if eq_body and eq_body not in ('crown',):
        body = _SEASON_BODY_MAP.get(eq_body, _get_char_body(level, char.get('class_id', ''), ''))
    else:
        body = _get_char_body(level, char.get('class_id', ''), eq_body)
    crown = '👑' if eq_body == 'crown' else ''

    tier_label = ("NEULING" if level < 5 else "ABENTEURER" if level < 15 else
                  "KRIEGER" if level < 30 else "HELD" if level < 50 else
                  "CHAMPION" if level < 75 else "LEGENDE" if level < 100 else "GOTTHEIT")
    tier_col = ("#888" if level < 5 else "#27ae60" if level < 15 else "#00d4ff" if level < 30
                else "#ffd700" if level < 50 else "#ff9500" if level < 75
                else "#ff00ff" if level < 100 else "#ffd700")
    eq_title = char.get('equipped_title', '') or ''

    # Returns full self-contained HTML for use with components.v1.html()
    return f"""<!DOCTYPE html>
<html><head><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:transparent;font-family:-apple-system,BlinkMacSystemFont,sans-serif}}
@keyframes float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-12px)}}}}
@keyframes pulse{{0%,100%{{opacity:.5;transform:scale(.95)}}50%{{opacity:1;transform:scale(1.08)}}}}
</style></head>
<body>
<div style="position:relative;text-align:center;padding:24px 14px 16px;
  background:linear-gradient(160deg,rgba(255,255,255,0.07),rgba(255,255,255,0.02));
  border-radius:18px;border:1px solid rgba(255,255,255,0.1);overflow:hidden;height:100%">
  <div style="position:absolute;top:8px;left:8px;background:{tier_col}25;
    border:1px solid {tier_col}55;border-radius:20px;padding:2px 8px;
    font-size:9px;font-weight:900;color:{tier_col};letter-spacing:2px">{tier_label}</div>
  <div style="position:absolute;top:8px;right:8px;background:rgba(0,0,0,0.5);
    border:1px solid rgba(255,255,255,0.15);border-radius:20px;padding:2px 8px;
    font-size:11px;font-weight:900;color:white">LVL {level}</div>
  <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-55%);
    width:120px;height:120px;border-radius:50%;
    border:1px solid {glow_col}44;
    animation:pulse 2.5s ease-in-out infinite;
    background:radial-gradient(circle,{glow_col}18 0%,transparent 70%)"></div>
  <div style="position:relative;display:inline-block;margin-top:18px">
    {f'<div style="font-size:26px;margin-bottom:-8px">{crown}</div>' if crown else '<div style="height:16px"></div>'}
    <div style="font-size:86px;line-height:1;animation:float 3s ease-in-out infinite;
      filter:drop-shadow(0 0 16px {glow_col})">{body}</div>
  </div>
  <div style="font-weight:900;color:white;font-size:19px;margin-top:8px">{char.get('name','Hero')}</div>
  {f'<div style="font-size:10px;color:{glow_col};letter-spacing:2px;font-weight:700;text-transform:uppercase;margin-top:2px">{eq_title}</div>' if eq_title else ''}
  <div style="font-size:12px;color:rgba(255,255,255,0.4);margin-top:3px">{ci.get('icon','⭐')} {ci.get('name','Held')}</div>
</div>
</body></html>"""


def _render_char_setup():
    st.markdown("## ⚔️ Erstelle deinen Charakter")
    st.markdown("Wähle Klasse und Namen, um dein Produktivitäts-Abenteuer zu beginnen.")
    st.markdown("")
    with st.form("char_setup_form"):
        name = st.text_input("Dein Heldenname", placeholder="z.B. Angelo")
        st.markdown("#### Klasse wählen")
        class_options = [
            f"{v['icon']} {v['name']} — {v['bonus_desc']}" for v in CLASS_INFO.values()
        ]
        class_keys = list(CLASS_INFO.keys())
        chosen_idx = st.radio("", class_options, index=0, label_visibility="collapsed")
        idx = class_options.index(chosen_idx)
        if st.form_submit_button("⚔️ Abenteuer beginnen!", use_container_width=True, type="primary"):
            if name.strip():
                save_character(name.strip(), class_keys[idx])
                award_xp(100, entry_type=None)
                st.success(f"🎊 Willkommen, {name.strip()}! Deine Reise beginnt!")
                st.rerun()
            else:
                st.warning("Bitte gib einen Namen ein.")


def _render_shop(current_level, coins):
    st.caption(f"💰 Du hast **{coins} Münzen** · Items nach Level gesperrt bis du es erreichst")
    st.write("")
    all_items = get_all_shop_items()
    owned_keys = {i['item_key'] for i in get_inventory()}
    CAT_LABELS = {
        'cosmetic_aura': '✨ Auras', 'cosmetic_body': '🎭 Outfits',
        'title': '📜 Titel', 'consumable': '⚡ Verbrauchsgüter', 'upgrade': '🔮 Permanente Upgrades'
    }
    from collections import defaultdict
    by_cat = defaultdict(list)
    for it in all_items:
        by_cat[it['category']].append(it)
    for cat in ['cosmetic_aura', 'cosmetic_body', 'title', 'consumable', 'upgrade']:
        items = by_cat.get(cat, [])
        if not items:
            continue
        st.markdown(f"#### {CAT_LABELS.get(cat, cat)}")
        cols = st.columns(3)
        for i, it in enumerate(items):
            with cols[i % 3]:
                rc = RARITY_COLORS.get(it['rarity'], '#636e72')
                locked = current_level < it['unlock_level']
                already_owned = it['item_key'] in owned_keys and not it['stackable']
                can_afford = coins >= it['cost_coins']
                opacity = "0.45" if locked else "1"
                st.markdown(f"""<div style="background:rgba(255,255,255,0.04);border-radius:12px;
                  padding:14px;border-top:3px solid {rc};border:1px solid {rc}33;
                  margin-bottom:6px;opacity:{opacity}">
                  <div style="font-size:30px;text-align:center;margin-bottom:6px">{it['icon']}</div>
                  <div style="font-weight:700;font-size:13px;text-align:center">{it['name']}</div>
                  <div style="font-size:11px;color:rgba(255,255,255,0.45);text-align:center;margin:4px 0 8px">{it['description']}</div>
                  <div style="display:flex;justify-content:space-between">
                    <span style="font-size:10px;color:{rc};font-weight:700;text-transform:uppercase">{RARITY_LABELS.get(it['rarity'],it['rarity'])}</span>
                    <span style="color:#ffd700;font-weight:700;font-size:13px">🪙 {it['cost_coins']}</span>
                  </div>
                  {'<div style="font-size:10px;color:rgba(255,255,255,0.3);text-align:center;margin-top:6px">🔒 Entsperrt ab Level ' + str(it['unlock_level']) + '</div>' if locked else ''}
                </div>""", unsafe_allow_html=True)
                if already_owned:
                    st.markdown('<div style="text-align:center;font-size:12px;color:#00ff88">✅ Besessen</div>',
                                unsafe_allow_html=True)
                elif locked:
                    st.button(f"🔒 Ab Lvl {it['unlock_level']}", key=f"buy_{it['item_key']}",
                               disabled=True, use_container_width=True)
                elif not can_afford:
                    st.button(f"💸 {it['cost_coins']} Münzen", key=f"buy_{it['item_key']}",
                               disabled=True, use_container_width=True)
                else:
                    if st.button(f"Kaufen · 🪙 {it['cost_coins']}", key=f"buy_{it['item_key']}",
                                  use_container_width=True, type="primary"):
                        ok, msg = buy_item(it['item_key'])
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
        st.markdown("")


def _render_inventory():
    inv = get_inventory()
    if not inv:
        st.info("Dein Inventar ist leer — geh in den Shop und kaufe dein erstes Item! 🛒")
        return
    for it in inv:
        rc = RARITY_COLORS.get(it['rarity'], '#636e72')
        is_eq = it['equipped']
        uses = it['uses_remaining']
        uses_txt = f"· {uses}× übrig" if uses > 0 else "· ∞ Verwendungen" if uses < 0 else "· verbraucht"
        eq_badge = f' <span style="color:{rc};font-size:10px;font-weight:700">[AKTIV]</span>' if is_eq else ''
        c1, c2, c3 = st.columns([0.4, 2.8, 1.5])
        with c1:
            st.markdown(f'<div style="font-size:34px;text-align:center;padding:4px 0">{it["icon"]}</div>',
                        unsafe_allow_html=True)
        with c2:
            st.markdown(f'<strong style="color:white">{it["name"]}</strong>{eq_badge}',
                        unsafe_allow_html=True)
            st.caption(f'{RARITY_LABELS.get(it["rarity"], it["rarity"])} · {it["description"][:50]} {uses_txt}')
        with c3:
            if it['category'] in ('cosmetic_aura', 'cosmetic_body', 'title'):
                lbl = "Ablegen" if is_eq else "Anlegen"
                if st.button(lbl, key=f"eq_{it['id']}", use_container_width=True,
                              type="primary" if not is_eq else "secondary"):
                    equip_item(it['id'], it['item_key'], it['category'])
                    st.rerun()
            elif it['category'] == 'consumable' and uses != 0:
                if st.button("Verwenden", key=f"use_{it['id']}", use_container_width=True):
                    ok, msg = use_item(it['id'])
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        st.markdown('<hr style="border-color:rgba(255,255,255,0.05);margin:4px 0">', unsafe_allow_html=True)


def render_character_page():
    st.markdown(URGENCY_CSS, unsafe_allow_html=True)

    char = get_character()
    if not char or not char.get('class_id'):
        _render_char_setup()
        return

    level, xp_cur, xp_next = compute_level(char['total_xp'])

    # ── Level-up notification ──────────────────────────────────────
    if st.session_state.get('levelup_queue'):
        for notif in st.session_state.levelup_queue:
            st.balloons()
            st.success(f"🎊 LEVEL UP! Du bist jetzt **Level {notif['level']}**! +{notif['coins']} 🪙 Münzen verdient!")
        del st.session_state['levelup_queue']

    # ── Header: Charakter-Card + Stats ────────────────────────────
    col_vis, col_stats = st.columns([1, 1.8])
    ci = CLASS_INFO.get(char.get('class_id', ''), {})
    pct = int(xp_cur / xp_next * 100) if xp_next > 0 else 0
    xp_bar_col = ci.get('color', '#00d4ff')

    with col_vis:
        components.html(_build_char_visual(char, level), height=310)

    with col_stats:
        # Season pass progress
        sp_data = get_player_season()
        s_id = sp_data['season_id']
        s_xp = sp_data['season_xp']
        season = next((s for s in SEASON_PASS_DATA if s['id'] == s_id), SEASON_PASS_DATA[0])
        claimed = get_season_claimed(s_id)
        unclaimed_tiers = [t for t in season['tiers'] if s_xp >= t['xp'] and t['tier'] not in claimed]

        active_boosts = []
        xp_exp = get_setting('xp_boost_expiry', '')
        if xp_exp:
            try:
                if datetime.fromisoformat(xp_exp) > datetime.utcnow():
                    active_boosts.append("⚡ XP-Boost")
            except Exception:
                pass
        if get_setting('streak_shield_active', ''):
            active_boosts.append("🛡️ Streak-Schild")
        boost_html = " ".join(f'<span style="background:#ffd70033;color:#ffd700;font-size:10px;padding:1px 7px;border-radius:10px;font-weight:700">{b}</span>' for b in active_boosts) if active_boosts else ''

        stats_html = f"""<!DOCTYPE html><html><head><style>
        *{{margin:0;padding:0;box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,sans-serif}}
        body{{background:transparent;color:white;padding:8px 4px}}
        </style></head><body>
        <div style="font-size:10px;color:rgba(255,255,255,0.4);letter-spacing:2px;text-transform:uppercase;margin-bottom:3px">KLASSE</div>
        <div style="font-size:14px;font-weight:700;margin-bottom:14px">{ci.get('icon','⭐')} {ci.get('name','Held')} <span style="color:rgba(255,255,255,0.4);font-size:11px">— {ci.get('bonus_desc','')}</span></div>
        <div style="font-size:10px;color:rgba(255,255,255,0.4);letter-spacing:2px;text-transform:uppercase;margin-bottom:2px">LEVEL</div>
        <div style="font-size:46px;font-weight:900;color:{xp_bar_col};line-height:1;margin-bottom:10px">{level}</div>
        <div style="background:rgba(255,255,255,0.12);border-radius:8px;height:11px;overflow:hidden;margin-bottom:5px">
          <div style="width:{pct}%;height:100%;border-radius:8px;background:linear-gradient(90deg,{xp_bar_col},{xp_bar_col}99);box-shadow:0 0 8px {xp_bar_col}66"></div>
        </div>
        <div style="font-size:11px;color:rgba(255,255,255,0.45);margin-bottom:2px">{xp_cur:,} / {xp_next:,} XP</div>
        <div style="font-size:10px;color:rgba(255,255,255,0.3);margin-bottom:14px">Gesamt: {char['total_xp']:,} XP</div>
        <div style="font-size:22px;font-weight:900;color:#ffd700;margin-bottom:10px">💰 {char['coins']} Münzen</div>
        <div style="font-size:10px;color:rgba(255,255,255,0.4);letter-spacing:2px;text-transform:uppercase;margin-bottom:4px">SEASON PASS</div>
        <div style="font-size:12px;font-weight:700;color:{season['color']};margin-bottom:6px">{season['icon']} {season['name']}</div>
        <div style="background:rgba(255,255,255,0.1);border-radius:6px;height:8px;overflow:hidden;margin-bottom:4px">
          <div style="width:{min(100,int(s_xp / max(1,season['tiers'][-1]['xp'])*100))}%;height:100%;background:linear-gradient(90deg,{season['color']},{season['color']}99)"></div>
        </div>
        <div style="font-size:10px;color:rgba(255,255,255,0.35);margin-bottom:6px">Season XP: {s_xp:,} · {"🎁 " + str(len(unclaimed_tiers)) + " Belohnungen verfügbar!" if unclaimed_tiers else "Auf dem aktuellen Stand"}</div>
        {boost_html}
        </body></html>"""
        components.html(stats_html, height=310)

    st.markdown("---")

    # ── Tabs ────────────────────────────────────────────────────────
    tab_shop, tab_inv, tab_hist = st.tabs(["🛒 Shop", "🎒 Inventar", "📜 Level-Geschichte"])

    with tab_shop:
        _render_shop(level, char['coins'])

    with tab_inv:
        _render_inventory()

    with tab_hist:
        hist = get_level_history()
        if not hist:
            st.info("Noch kein Level-Up — erledige Quests und sammle XP!")
        else:
            for lvl, coins_e, ts in hist:
                ts_short = ts[:10] if ts else "?"
                tier_c = "#ff00ff" if lvl >= 100 else "#ffd700" if lvl >= 50 else "#00d4ff" if lvl >= 25 else "#27ae60" if lvl >= 10 else "#636e72"
                st.markdown(f"""<div style="display:flex;align-items:center;gap:12px;padding:8px 14px;
                  background:rgba(255,255,255,0.03);border-radius:10px;margin-bottom:6px;
                  border-left:3px solid {tier_c}">
                  <div style="font-size:24px;font-weight:900;color:{tier_c};min-width:60px">LVL {lvl}</div>
                  <div style="flex:1;font-size:13px;color:rgba(255,255,255,0.6)">{ts_short}</div>
                  <div style="color:#ffd700;font-weight:700">+{coins_e} 🪙</div>
                </div>""", unsafe_allow_html=True)


def render_habit_tracker_page():
    st.markdown(URGENCY_CSS, unsafe_allow_html=True)
    st.title("🔁 Habit Tracker")
    st.caption("Adaptiv — 50% Kraft + 50% Effort = 100% für heute")

    today = date.today().isoformat()

    # ── Energy Calibration ─────────────────────────────────────────
    st.markdown("#### 🔋 Heutige Energie")
    energy = st.slider("", 10, 100, value=get_today_energy(), step=10,
                        key="energy_dial", label_visibility="collapsed")
    set_today_energy(energy)

    _elabels = {10:"😴 Kaum da",20:"🥱 Sehr müde",30:"😞 Wenig Kraft",40:"😐 Unter Normal",
                50:"🙂 Halbe Kraft",60:"😊 Okay",70:"💪 Gut drauf",80:"🔥 Stark",
                90:"⚡ Sehr stark",100:"🚀 Vollgas"}
    elabel = _elabels.get(energy, f"{energy}%")
    bcol = ("#ff4444" if energy < 30 else "#ffd700" if energy < 50 else
            "#00d4ff" if energy < 80 else "#00ff88")

    st.markdown(f"""<div style="background:rgba(255,255,255,0.04);border-radius:10px;
        padding:10px 16px;border:1px solid rgba(255,255,255,0.08);margin:-10px 0 22px">
      <div style="display:flex;align-items:center;gap:14px">
        <div style="flex:1;background:rgba(255,255,255,0.1);border-radius:6px;height:10px;overflow:hidden">
          <div style="width:{energy}%;height:100%;border-radius:6px;
            background:linear-gradient(90deg,{bcol},{bcol}bb);
            box-shadow:0 0 10px {bcol}66"></div>
        </div>
        <span style="font-weight:900;color:white;font-size:20px;min-width:48px">{energy}%</span>
        <span style="color:rgba(255,255,255,0.5);font-size:14px">{elabel}</span>
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Today's Habits ─────────────────────────────────────────────
    habits = get_habits()

    if habits:
        st.markdown("#### Heute")
        per_row = 4
        for row_start in range(0, len(habits), per_row):
            row_habits = habits[row_start:row_start + per_row]
            cols = st.columns(per_row)
            for col, habit in zip(cols, row_habits):
                with col:
                    log = get_habit_log(habit['id'], today)
                    comp = log['completion_pct'] if log else 0
                    score = adaptive_score(comp, energy)
                    st.markdown(_habit_ring_html(habit, score, comp), unsafe_allow_html=True)
                    new_comp = st.slider("", 0, 100, value=comp, step=10,
                                          key=f"hcomp_{habit['id']}",
                                          label_visibility="collapsed", format="%d%%")
                    if new_comp != comp:
                        log_habit(habit['id'], today, energy, new_comp)
                        st.rerun()
                    if st.button("×", key=f"hdel_{habit['id']}",
                                  help="Habit entfernen", use_container_width=True):
                        delete_habit(habit['id'])
                        st.rerun()
    else:
        st.info("Noch keine Habits — füge deinen ersten hinzu! 👇")

    # ── Add Habit ──────────────────────────────────────────────────
    with st.expander("➕ Neuen Habit hinzufügen"):
        with st.form("new_habit_form"):
            hc1, hc2, hc3 = st.columns([3, 1, 2])
            with hc1:
                h_name = st.text_input("Name", placeholder="z.B. 2L Wasser trinken")
            with hc2:
                h_icon = st.selectbox("Icon", HABIT_ICONS, key="hi_icon")
            with hc3:
                h_cat = st.selectbox("Kategorie", [
                    "Gesundheit","Fitness","Mental","Ernährung","Lernen","Schlaf","Sonstiges"
                ])
            h_color = st.color_picker("Farbe", value="#00d4ff")
            if st.form_submit_button("Habit erstellen", use_container_width=True, type="primary"):
                if h_name.strip():
                    add_habit(h_name.strip(), h_cat, h_icon, h_color)
                    st.success(f"✅ '{h_name}' erstellt!")
                    st.rerun()

    # ── Analytics ─────────────────────────────────────────────────
    if habits:
        st.markdown("---")
        st.markdown("### 📊 Analytics")
        tab1, tab2, tab3, tab4 = st.tabs(["🗓️ Heatmap", "🔥 Streaks", "🕸️ Wochenradar", "📈 Momentum"])

        with tab1:
            st.markdown("<small>Adaptive Performance der letzten 12 Wochen. "
                        "Farbe = normalisierte Leistung bei der jeweiligen Tagesenergie.</small>",
                        unsafe_allow_html=True)
            st.write("")
            for h in habits:
                st.markdown(_habit_heatmap_html(h), unsafe_allow_html=True)

        with tab2:
            st.markdown("<small>Konsekutive Tage mit adaptivem Score ≥ 80%</small>",
                        unsafe_allow_html=True)
            st.write("")
            _render_habit_streaks(habits)

        with tab3:
            _render_habit_radar(habits)

        with tab4:
            _render_habit_momentum(habits)


def render_settings_page():
    st.title("⚙️ Einstellungen")

    # ── Kategorien ─────────────────────────────────────────────────
    st.markdown("### 🏷️ Aufgaben-Kategorien")
    st.caption("Erstelle eigene Kategorien mit Icon, Farbe und XP-Wert. Der XP-Wert bestimmt, wie viel XP eine erledigte Aufgabe in dieser Kategorie bringt.")

    categories = get_categories()

    # Edit / delete existing
    for cat in categories:
        with st.expander(f"{cat['icon']} **{cat['name']}** — {cat['base_xp']} XP", expanded=False):
            with st.form(f"cat_edit_{cat['id']}"):
                ec1, ec2 = st.columns([2, 1])
                with ec1:
                    new_name  = st.text_input("Name", value=cat['name'], key=f"ce_name_{cat['id']}")
                    new_icon  = st.text_input("Icon (Emoji)", value=cat['icon'], key=f"ce_icon_{cat['id']}")
                with ec2:
                    new_color = st.color_picker("Farbe", value=cat['color'], key=f"ce_color_{cat['id']}")
                    new_xp    = st.number_input("Basis-XP", value=int(cat['base_xp']), min_value=10,
                                                max_value=1000, step=10, key=f"ce_xp_{cat['id']}")
                col_save, col_del = st.columns(2)
                with col_save:
                    if st.form_submit_button("💾 Speichern", use_container_width=True):
                        conn = sqlite3.connect(DB_PATH)
                        conn.execute("UPDATE task_categories SET name=?,icon=?,color=?,base_xp=? WHERE id=?",
                                     (new_name.strip(), new_icon.strip(), new_color, new_xp, cat['id']))
                        conn.commit()
                        conn.close()
                        st.success("Gespeichert!")
                        st.rerun()
                with col_del:
                    if st.form_submit_button("🗑️ Löschen", use_container_width=True):
                        conn = sqlite3.connect(DB_PATH)
                        conn.execute("UPDATE entries SET category_id=NULL WHERE category_id=?", (cat['id'],))
                        conn.execute("DELETE FROM task_categories WHERE id=?", (cat['id'],))
                        conn.commit()
                        conn.close()
                        st.rerun()

    st.markdown("---")
    st.markdown("##### ➕ Neue Kategorie")
    with st.form("cat_add_form"):
        nc1, nc2 = st.columns([2, 1])
        with nc1:
            add_name  = st.text_input("Name", placeholder="z.B. Kreativarbeit")
            add_icon  = st.text_input("Icon", value="📌", placeholder="Emoji")
        with nc2:
            add_color = st.color_picker("Farbe", value="#636e72")
            add_xp    = st.number_input("Basis-XP", value=100, min_value=10, max_value=1000, step=10)
        if st.form_submit_button("Kategorie erstellen", use_container_width=True):
            if add_name.strip():
                conn = sqlite3.connect(DB_PATH)
                conn.execute(
                    "INSERT INTO task_categories (name,icon,color,base_xp,sort_order) VALUES (?,?,?,?,?)",
                    (add_name.strip(), add_icon.strip() or "📌", add_color, add_xp,
                     len(categories))
                )
                conn.commit()
                conn.close()
                st.success(f"Kategorie '{add_name}' erstellt!")
                st.rerun()

    # ── Datensicherung / Cloud Backup ──────────────────────────────
    st.markdown("---")
    st.markdown("### ☁️ Datensicherung")
    st.caption("Alle Daten werden lokal in `kaizen.db` gespeichert. Auf Streamlit Cloud wird die DB bei jedem Redeploy gelöscht — hinterlege hier einen GitHub Token für automatisches Backup.")

    last_backup = get_setting("last_backup", "")
    backup_gist = get_setting("backup_gist_id", "")

    col_status, col_action = st.columns([2, 1])
    with col_status:
        if last_backup:
            try:
                lb = datetime.fromisoformat(last_backup)
                mins_ago = int((datetime.utcnow() - lb).total_seconds() / 60)
                st.success(f"✅ Letztes Backup: vor {mins_ago} Min | Gist: `{backup_gist[:8]}...`" if backup_gist else f"✅ Letztes Backup: {last_backup[:16]}")
            except Exception:
                st.info("Backup konfiguriert.")
        else:
            st.warning("⚠️ Kein Backup eingerichtet — Daten gehen bei Redeploy verloren.")

    with col_action:
        if st.button("🔄 Backup jetzt", key="manual_backup"):
            with st.spinner("Sichere..."):
                ok = auto_backup_db()
            if ok:
                st.rerun()
            else:
                st.error("Fehler — Token hinterlegen und speichern, dann nochmal.")

    with st.expander("🔧 Backup einrichten"):
        st.markdown("""
**So geht's in 2 Minuten:**
1. Gehe zu [github.com/settings/tokens](https://github.com/settings/tokens) → *Generate new token (classic)*
2. Nur `gist`-Berechtigung aktivieren
3. Token hier eintragen → einmal manuell backupen → Gist-ID wird automatisch gespeichert

**Für Streamlit Cloud:** Trage in den App-Secrets ein:
```
GITHUB_BACKUP_TOKEN = "ghp_deintoken"
GITHUB_BACKUP_GIST_ID = "deine_gist_id"  # nach erstem Backup automatisch gesetzt
```
        """)
        with st.form("backup_creds_form"):
            new_token = st.text_input("GitHub Token (gist-Berechtigung)", type="password",
                                      placeholder="ghp_...",
                                      key="backup_token_inp")
            new_gist  = st.text_input("Gist ID (leer = wird beim ersten Backup erstellt)",
                                      value=backup_gist, key="backup_gist_inp")
            if st.form_submit_button("Speichern"):
                if new_token.strip():
                    set_setting("backup_github_token", new_token.strip())
                if new_gist.strip():
                    set_setting("backup_gist_id", new_gist.strip())
                st.success("Gespeichert — klick 'Backup jetzt' zum Testen.")
                st.rerun()

    if backup_gist:
        with st.expander("📥 Backup wiederherstellen"):
            st.warning("⚠️ Überschreibt die lokale Datenbank mit dem letzten Backup!")
            if st.button("Jetzt wiederherstellen", key="manual_restore"):
                with st.spinner("Wiederherstelle..."):
                    ok = auto_restore_db()
                if ok:
                    st.success("✅ Wiederhergestellt — App neu laden.")
                    st.rerun()
                else:
                    st.error("Fehler — Backup nicht gefunden oder Token ungültig.")


def render_season_pass_page():
    st.markdown(URGENCY_CSS, unsafe_allow_html=True)

    sp = get_player_season()
    season_id = sp['season_id']
    season_xp = sp['season_xp']
    season = next((s for s in SEASON_PASS_DATA if s['id'] == season_id), SEASON_PASS_DATA[0])
    claimed = get_season_claimed(season_id)
    tiers = season['tiers']
    max_xp = tiers[-1]['xp']
    pct = min(100, int(season_xp / max_xp * 100)) if max_xp > 0 else 0

    # Season header
    season_col = season['color']
    unclaimed = [t for t in tiers if season_xp >= t['xp'] and t['tier'] not in claimed]

    header_html = f"""<!DOCTYPE html><html><head><style>
    *{{margin:0;padding:0;box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,sans-serif}}
    body{{background:transparent;padding:4px 0}}
    @keyframes glow{{0%,100%{{box-shadow:0 0 20px {season_col}44}}50%{{box-shadow:0 0 40px {season_col}88}}}}
    </style></head><body>
    <div style="background:linear-gradient(135deg,{season_col}22,{season_col}08);
      border:1px solid {season_col}44;border-radius:16px;padding:20px 24px;animation:glow 3s ease-in-out infinite">
      <div style="display:flex;align-items:center;gap:16px;margin-bottom:14px">
        <div style="font-size:48px">{season['icon']}</div>
        <div>
          <div style="font-size:10px;color:rgba(255,255,255,0.4);letter-spacing:3px;text-transform:uppercase">SEASON {season_id}</div>
          <div style="font-size:26px;font-weight:900;color:white">{season['name']}</div>
          <div style="font-size:12px;color:{season_col};font-weight:600">Season XP: {season_xp:,} / {max_xp:,}</div>
        </div>
        {'<div style="margin-left:auto;background:#ffd70033;border:1px solid #ffd70055;border-radius:12px;padding:8px 16px;text-align:center"><div style="font-size:22px">🎁</div><div style="font-size:11px;color:#ffd700;font-weight:700">' + str(len(unclaimed)) + ' verfügbar</div></div>' if unclaimed else ''}
      </div>
      <div style="background:rgba(0,0,0,0.3);border-radius:10px;height:14px;overflow:hidden;margin-bottom:6px">
        <div style="width:{pct}%;height:100%;border-radius:10px;
          background:linear-gradient(90deg,{season_col},{season_col}bb);
          box-shadow:0 0 12px {season_col}88;transition:width 1s ease"></div>
      </div>
      <div style="font-size:11px;color:rgba(255,255,255,0.4)">
        Tier {len(claimed)} / {len(tiers)} abgeschlossen · {pct}% der Season abgeschlossen
      </div>
    </div>
    </body></html>"""
    components.html(header_html, height=160)

    if unclaimed:
        st.markdown(f"### 🎁 Belohnungen einlösen ({len(unclaimed)})")
        cols_claim = st.columns(min(4, len(unclaimed)))
        for idx, tier in enumerate(unclaimed[:4]):
            rarity_col = RARITY_COLORS.get(
                next((i[6] for i in SEASON_EXCLUSIVE_ITEMS if i[0] == tier['value']), 'common'), '#636e72'
            ) if tier['type'] == 'item' else ('#ffd700' if tier['type'] == 'title' else '#27ae60')
            with cols_claim[idx % len(cols_claim)]:
                st.markdown(f"""<div style="background:{rarity_col}18;border:1px solid {rarity_col}44;
                  border-radius:12px;padding:12px;text-align:center;margin-bottom:6px">
                  <div style="font-size:28px">{tier['icon']}</div>
                  <div style="font-size:11px;font-weight:700;color:white;margin:4px 0 2px">{tier['name']}</div>
                  <div style="font-size:9px;color:rgba(255,255,255,0.4)">Tier {tier['tier']}</div>
                </div>""", unsafe_allow_html=True)
                if st.button(f"Einlösen", key=f"claim_{season_id}_{tier['tier']}"):
                    ok, msg = claim_season_reward(season_id, tier['tier'])
                    if ok:
                        st.success(msg)
                        advance_season_if_complete()
                        st.rerun()
                    else:
                        st.error(msg)
        if len(unclaimed) > 4:
            if st.button(f"Alle {len(unclaimed)} Belohnungen auf einmal einlösen"):
                msgs = []
                for tier in unclaimed:
                    ok, msg = claim_season_reward(season_id, tier['tier'])
                    if ok:
                        msgs.append(msg)
                advance_season_if_complete()
                st.success(f"✅ {len(msgs)} Belohnungen erhalten!")
                st.rerun()

    st.markdown("---")
    st.markdown("### Alle Tiers")

    # Render tier grid using components.html for guaranteed visual fidelity
    def _render_tier_grid(tiers, season_xp, claimed, season_col):
        cells = []
        for t in tiers:
            unlocked = season_xp >= t['xp']
            is_claimed = t['tier'] in claimed
            is_current = not is_claimed and unlocked

            if is_claimed:
                bg = '#27ae6022'; border = '#27ae6055'; icon_display = f'<div style="font-size:20px">{t["icon"]}</div><div style="font-size:14px;color:#27ae60">✓</div>'
                opacity = '1'
            elif is_current:
                bg = f'{season_col}30'; border = f'{season_col}88'; icon_display = f'<div style="font-size:22px">{t["icon"]}</div>'
                opacity = '1'
            else:
                bg = 'rgba(255,255,255,0.04)'; border = 'rgba(255,255,255,0.08)'; icon_display = f'<div style="font-size:22px;filter:grayscale(1);opacity:0.3">{t["icon"]}</div>'
                opacity = '0.6'

            glow = f'box-shadow:0 0 12px {season_col}66;' if is_current else ''
            cells.append(f"""
            <div title="Tier {t['tier']}: {t['name']} ({t['xp']:,} XP)" style="
              background:{bg};border:1px solid {border};border-radius:10px;
              padding:8px 4px;text-align:center;{glow}opacity:{opacity};
              display:flex;flex-direction:column;align-items:center;justify-content:center;
              min-height:62px">
              {icon_display}
              <div style="font-size:9px;color:rgba(255,255,255,0.4);margin-top:3px">T{t['tier']}</div>
            </div>""")

        rows_html = ""
        for row_start in range(0, len(cells), 10):
            row_cells = cells[row_start:row_start+10]
            rows_html += f'<div style="display:grid;grid-template-columns:repeat(10,1fr);gap:6px;margin-bottom:8px">{"".join(row_cells)}</div>'

        return f"""<!DOCTYPE html><html><head><style>
        *{{margin:0;padding:0;box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,sans-serif}}
        body{{background:transparent;padding:4px 0}}
        </style></head><body>{rows_html}</body></html>"""

    tier_html = _render_tier_grid(tiers, season_xp, claimed, season_col)
    components.html(tier_html, height=390)

    # Tier detail on click (show next 3 upcoming rewards)
    st.markdown("##### Nächste Belohnungen")
    upcoming = [t for t in tiers if t['tier'] not in claimed][:5]
    if upcoming:
        cols_up = st.columns(len(upcoming))
        for idx, t in enumerate(upcoming):
            unlocked = season_xp >= t['xp']
            rarity_col = ('#ffd700' if t['type'] == 'title' else '#27ae60' if t['type'] == 'coins'
                          else RARITY_COLORS.get(next((i[6] for i in SEASON_EXCLUSIVE_ITEMS if i[0] == t['value']), 'common'), '#636e72'))
            status_text = "🔓 Bereit!" if unlocked else f"🔒 {t['xp']:,} XP"
            with cols_up[idx]:
                st.markdown(f"""<div style="background:{rarity_col}14;border:1px solid {rarity_col}33;
                  border-radius:10px;padding:10px 8px;text-align:center">
                  <div style="font-size:24px">{t['icon']}</div>
                  <div style="font-size:11px;font-weight:700;color:white;margin:4px 0 2px">{t['name']}</div>
                  <div style="font-size:9px;color:rgba(255,255,255,0.4);margin-bottom:4px">Tier {t['tier']}</div>
                  <div style="font-size:10px;color:{rarity_col};font-weight:600">{status_text}</div>
                </div>""", unsafe_allow_html=True)
    else:
        st.success("🏆 Alle Tiers dieser Season abgeschlossen! Nächste Season freigeschaltet!")

    # Season overview at bottom
    with st.expander("Andere Seasons anzeigen"):
        for s in SEASON_PASS_DATA:
            is_current = s['id'] == season_id
            is_done = s['id'] < season_id
            status = "✅ Abgeschlossen" if is_done else ("▶️ Aktiv" if is_current else "🔒 Gesperrt")
            st.markdown(f"**{s['icon']} Season {s['id']}: {s['name']}** — {status}")


def render_statistics_page():
    st.markdown(URGENCY_CSS, unsafe_allow_html=True)
    st.title("📊 Statistiken")

    stats = get_analytics_stats()
    records = get_personal_records()
    rate = (stats['completed'] / stats['total'] * 100) if stats['total'] > 0 else 0

    # ── KPI Cards ─────────────────────────────────────────────────
    kpi = "text-align:center;background:rgba(255,255,255,0.05);border-radius:12px;padding:16px 8px;border:1px solid rgba(255,255,255,0.09)"
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.markdown(f'<div style="{kpi}"><div style="font-size:32px;font-weight:900;color:#00d4ff">{stats["completed"]}</div><div style="color:rgba(255,255,255,0.45);font-size:11px;margin-top:4px">✅ Erledigt</div></div>', unsafe_allow_html=True)
    k2.markdown(f'<div style="{kpi}"><div style="font-size:32px;font-weight:900;color:white">{stats["total"]}</div><div style="color:rgba(255,255,255,0.45);font-size:11px;margin-top:4px">📝 Gesamt</div></div>', unsafe_allow_html=True)
    k3.markdown(f'<div style="{kpi}"><div style="font-size:32px;font-weight:900;color:#ffd700">{rate:.1f}%</div><div style="color:rgba(255,255,255,0.45);font-size:11px;margin-top:4px">📈 Erfolgsquote</div></div>', unsafe_allow_html=True)
    k4.markdown(f'<div style="{kpi}"><div style="font-size:32px;font-weight:900;color:#ff9500">{records["total_hours"]}</div><div style="color:rgba(255,255,255,0.45);font-size:11px;margin-top:4px">⏱️ Fokus-Stunden</div></div>', unsafe_allow_html=True)
    k5.markdown(f'<div style="{kpi}"><div style="font-size:32px;font-weight:900;color:#00ff88">{records["active_days_30"]}</div><div style="color:rgba(255,255,255,0.45);font-size:11px;margin-top:4px">📅 Aktive Tage (30d)</div></div>', unsafe_allow_html=True)

    st.write("")

    # ── Charts Row 1: Typ-Verteilung + Wochentag ──────────────────
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Aufgaben nach Typ")
        if stats['type_stats']:
            df_t = pd.DataFrame(stats['type_stats'], columns=['Type','Count','Avg_Sec','Total_Sec'])
            df_t['Avg_Min'] = (df_t['Avg_Sec'] / 60).round(1)
            fig_pie = px.pie(df_t, values='Count', names='Type',
                             color_discrete_sequence=['#00d4ff','#ff6b6b','#ffd93d'],
                             hole=0.45)
            fig_pie.update_traces(textfont_size=13, textinfo='label+percent')
            fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', showlegend=True,
                                   font=dict(color='white'), margin=dict(t=10,b=10))
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Noch keine erledigten Aufgaben")

    with col_r:
        st.subheader("Produktivster Wochentag")
        wd_stats = get_weekday_stats()
        if wd_stats:
            wd_map = {0:"So",1:"Mo",2:"Di",3:"Mi",4:"Do",5:"Fr",6:"Sa"}
            wd_df = pd.DataFrame(wd_stats, columns=['wd','tasks','secs'])
            wd_df['day'] = wd_df['wd'].map(wd_map)
            wd_df['Minuten'] = (wd_df['secs'] / 60).round(1)
            # Sort Mon-Sun
            order = ["Mo","Di","Mi","Do","Fr","Sa","So"]
            wd_df['day'] = pd.Categorical(wd_df['day'], categories=order, ordered=True)
            wd_df = wd_df.sort_values('day')
            fig_wd = go.Figure(go.Bar(
                x=wd_df['day'], y=wd_df['tasks'],
                marker=dict(
                    color=wd_df['tasks'],
                    colorscale=[[0,'rgba(0,212,255,0.3)'],[1,'#00d4ff']],
                    showscale=False
                ),
                text=wd_df['tasks'], textposition='outside',
                hovertemplate='%{x}: %{y} Aufgaben<extra></extra>'
            ))
            fig_wd.update_layout(
                template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(5,8,15,0.4)',
                yaxis=dict(gridcolor='rgba(255,255,255,0.06)', title='Aufgaben'),
                xaxis=dict(gridcolor='rgba(255,255,255,0.06)'),
                margin=dict(t=10, b=30, l=40, r=10), height=280
            )
            st.plotly_chart(fig_wd, use_container_width=True)
        else:
            st.info("Noch keine Daten")

    st.markdown("---")

    # ── Täglicher Trend ────────────────────────────────────────────
    st.subheader("Täglicher Fortschritt (30 Tage)")
    if stats['daily_trend']:
        df_d = pd.DataFrame(stats['daily_trend'], columns=['Date','Count','Total_Sec'])
        df_d['Minuten'] = (df_d['Total_Sec'] / 60).round(1)
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=df_d['Date'], y=df_d['Count'], mode='lines+markers', name='Aufgaben',
            line=dict(color='#00d4ff', width=3),
            fill='tozeroy', fillcolor='rgba(0,212,255,0.08)'
        ))
        fig_trend.add_trace(go.Scatter(
            x=df_d['Date'], y=df_d['Minuten'], mode='lines+markers', name='Minuten',
            line=dict(color='#ff6b6b', width=2, dash='dot'),
            yaxis='y2'
        ))
        fig_trend.update_layout(
            hovermode='x unified', template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(5,8,15,0.4)',
            yaxis=dict(title='Aufgaben', gridcolor='rgba(255,255,255,0.06)'),
            yaxis2=dict(title='Minuten', overlaying='y', side='right',
                        gridcolor='rgba(255,255,255,0.04)'),
            margin=dict(t=10, b=40, l=50, r=60), height=300,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0)
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Noch keine Daten für den Trend")

    st.markdown("---")

    # ── Ø Dauer pro Typ ────────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Ø Fokus-Zeit pro Typ")
        if stats['type_stats']:
            df_t2 = pd.DataFrame(stats['type_stats'], columns=['Type','Count','Avg_Sec','Total_Sec'])
            df_t2['Avg_Min'] = (df_t2['Avg_Sec'] / 60).round(1)
            fig_bar = px.bar(df_t2, x='Type', y='Avg_Min', color='Type', text='Avg_Min',
                              color_discrete_sequence=['#00d4ff','#ff6b6b','#ffd93d'])
            fig_bar.update_traces(texttemplate='%{text} Min', textposition='outside')
            fig_bar.update_layout(
                template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(5,8,15,0.4)', showlegend=False,
                yaxis=dict(title='Minuten', gridcolor='rgba(255,255,255,0.06)'),
                margin=dict(t=10, b=30, l=50, r=10), height=280
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Keine Daten")

    # ── Personal Records ──────────────────────────────────────────
    with col_b:
        st.subheader("🏆 Persönliche Rekorde")
        rec_style = ("background:rgba(255,255,255,0.04);border-radius:10px;"
                     "padding:10px 14px;margin-bottom:8px;border:1px solid rgba(255,255,255,0.08)")
        if records['best_day']:
            st.markdown(f'<div style="{rec_style}">🥇 <strong>Bester Tag:</strong> '
                        f'{records["best_day"][0]} — {records["best_day"][1]} Aufgaben</div>',
                        unsafe_allow_html=True)
        if records['best_time_day']:
            mins = round(records['best_time_day'][1] / 60)
            st.markdown(f'<div style="{rec_style}">⏱️ <strong>Meiste Fokuszeit:</strong> '
                        f'{records["best_time_day"][0]} — {mins} Min</div>',
                        unsafe_allow_html=True)
        if records['longest']:
            lmins = round(records['longest'][1] / 60)
            name = records['longest'][0][:40] + "…" if len(records['longest'][0]) > 40 else records['longest'][0]
            st.markdown(f'<div style="{rec_style}">🔥 <strong>Längste Session:</strong> '
                        f'{lmins} Min<br><small style="color:rgba(255,255,255,0.4)">{name}</small></div>',
                        unsafe_allow_html=True)
        total_h = records['total_hours']
        st.markdown(f'<div style="{rec_style}">🎯 <strong>Fokus-Zeit gesamt:</strong> '
                    f'{total_h} Stunden</div>', unsafe_allow_html=True)


# ========== CALISTHENICS TRAININGSSEITE ==========

def _cal_heatmap_html(days=84):
    today_d = date.today()
    streak = get_cal_streak()
    date_set = streak['dates']

    def cell_color(active):
        return "#00ff88" if active else "rgba(255,255,255,0.05)"

    cells = ""
    for i in range(days - 1, -1, -1):
        d = today_d - timedelta(days=i)
        active = d.isoformat() in date_set
        tip = f"{d.strftime('%d.%m')}: {'trainiert' if active else 'Pause'}"
        cells += f'<div title="{tip}" style="width:14px;height:14px;background:{cell_color(active)};border-radius:2px;flex-shrink:0"></div>'

    return f"""<div style="background:rgba(255,255,255,0.03);border-radius:12px;padding:14px 16px;
  border:1px solid rgba(255,255,255,0.07);margin-bottom:10px">
  <div style="display:flex;flex-wrap:wrap;gap:3px;width:calc(14*(14px + 3px))">
    {cells}
  </div>
  <div style="display:flex;gap:8px;align-items:center;margin-top:8px;font-size:10px;color:rgba(255,255,255,0.3)">
    <div style="width:10px;height:10px;background:rgba(255,255,255,0.05);border-radius:2px"></div>
    <span>Pause</span>
    <div style="width:10px;height:10px;background:#00ff88;border-radius:2px;margin-left:8px"></div>
    <span>trainiert</span>
  </div>
</div>"""


def _cal_track_ladder_html(track):
    info = CAL_TRACKS[track]
    levels = info['levels']
    prog = get_cal_progress()[track]
    cur_idx = prog['level']

    steps = ""
    for i, lvl in enumerate(levels):
        if i < cur_idx:
            bg, col, icon = info['color'], "#fff", "✓"
        elif i == cur_idx:
            bg, col, icon = info['color'], "#fff", str(i + 1)
        else:
            bg, col, icon = "rgba(255,255,255,0.05)", "rgba(255,255,255,0.3)", str(i + 1)
        glow = f"box-shadow:0 0 12px {info['color']}99;" if i == cur_idx else ""
        opacity = "opacity:1" if i <= cur_idx else "opacity:0.5"
        steps += f"""
  <div style="display:flex;align-items:center;gap:10px;{opacity};margin-bottom:6px">
    <div style="width:26px;height:26px;border-radius:50%;background:{bg};color:{col};
                display:flex;align-items:center;justify-content:center;font-size:11px;
                font-weight:800;flex-shrink:0;{glow}">{icon}</div>
    <div style="font-size:12.5px;color:{'white' if i <= cur_idx else 'rgba(255,255,255,0.4)'};
                font-weight:{'700' if i == cur_idx else '400'}">{lvl['name']}</div>
  </div>"""

    is_max = cur_idx == len(levels) - 1
    bonus_note = ""
    if is_max and prog['bonus'] > 0:
        ex = get_cal_exercise(track, cur_idx, prog['bonus'])
        bonus_note = f"""<div style="margin-top:6px;font-size:11px;color:{info['color']};font-weight:700">
            ♾️ Unendlich-Modus: Ziel bereits auf {ex['target_reps']}{'s' if ex['hold'] else ' Wdh'} gesteigert</div>"""

    return f"""<div style="background:rgba(255,255,255,0.03);border-radius:14px;padding:16px 18px;
  border:1px solid {info['color']}33;height:100%">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
    <span style="font-size:20px">{info['icon']}</span>
    <span style="font-weight:800;color:white;font-size:13.5px">{info['full_label']}</span>
  </div>
  {steps}
  {bonus_note}
</div>"""


def render_training_page():
    st.title("🏋️ Training")
    st.caption("Calisthenics — jeden Tag ein Level weiter. Komplett zuhause, ohne Geräte.")

    sync_daily_training()
    streak = get_cal_streak()
    today_tracks = todays_cal_tracks()
    prog = get_cal_progress()

    # ── Hero: Streak ──────────────────────────────────────────
    flame = "🔥" if streak['current'] > 0 else "💤"
    trained_badge = ('<span style="background:rgba(46,204,113,0.18);color:#2ecc71;font-size:11px;'
                      'font-weight:700;padding:4px 12px;border-radius:20px;border:1px solid rgba(46,204,113,0.4)">'
                      '✅ Heute trainiert</span>') if streak['trained_today'] else \
                     ('<span style="background:rgba(243,156,18,0.18);color:#f39c12;font-size:11px;'
                      'font-weight:700;padding:4px 12px;border-radius:20px;border:1px solid rgba(243,156,18,0.4)">'
                      '⏳ Heute noch offen</span>')

    h1, h2, h3, h4 = st.columns(4)
    with h1:
        st.markdown(f"""<div style="text-align:center;background:rgba(255,255,255,0.03);border-radius:14px;
            padding:16px;border:1px solid rgba(255,255,255,0.08)">
            <div style="font-size:32px">{flame}</div>
            <div style="font-size:26px;font-weight:900;color:#ff9500">{streak['current']}</div>
            <div style="font-size:10px;color:rgba(255,255,255,0.4);letter-spacing:1px">TAGE STREAK</div>
        </div>""", unsafe_allow_html=True)
    with h2:
        st.markdown(f"""<div style="text-align:center;background:rgba(255,255,255,0.03);border-radius:14px;
            padding:16px;border:1px solid rgba(255,255,255,0.08)">
            <div style="font-size:32px">🏆</div>
            <div style="font-size:26px;font-weight:900;color:#ffd700">{streak['longest']}</div>
            <div style="font-size:10px;color:rgba(255,255,255,0.4);letter-spacing:1px">REKORD-STREAK</div>
        </div>""", unsafe_allow_html=True)
    with h3:
        st.markdown(f"""<div style="text-align:center;background:rgba(255,255,255,0.03);border-radius:14px;
            padding:16px;border:1px solid rgba(255,255,255,0.08)">
            <div style="font-size:32px">📋</div>
            <div style="font-size:26px;font-weight:900;color:#00d4ff">{streak['total_sessions']}</div>
            <div style="font-size:10px;color:rgba(255,255,255,0.4);letter-spacing:1px">EINHEITEN GESAMT</div>
        </div>""", unsafe_allow_html=True)
    with h4:
        st.markdown(f"""<div style="text-align:center;background:rgba(255,255,255,0.03);border-radius:14px;
            padding:16px;border:1px solid rgba(255,255,255,0.08);display:flex;flex-direction:column;
            justify-content:center;align-items:center">
            <div style="margin-bottom:6px">{trained_badge}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Heutiges Training ───────────────────────────────────────
    st.markdown("### 💪 Heutiges Training")
    entry_id, entry_done = get_todays_training_entry_id()

    if streak['trained_today']:
        st.success("Heute bereits geloggt — stark! Du kannst unten trotzdem nachtragen/korrigieren.")

    with st.form("cal_log_form"):
        inputs = {}
        for track in today_tracks:
            info = CAL_TRACKS[track]
            p = prog[track]
            ex = get_cal_exercise(track, p['level'], p['bonus'])
            unit = "Sekunden" if ex['hold'] else "Wiederholungen"

            st.markdown(f"""<div style="display:flex;align-items:center;gap:10px;margin:14px 0 4px 0">
                <span style="font-size:20px">{info['icon']}</span>
                <span style="font-weight:800;color:white;font-size:14px">{ex['name']}</span>
                <span style="font-size:10px;color:{info['color']};background:{info['color']}22;
                    padding:2px 8px;border-radius:10px;border:1px solid {info['color']}55">
                    Stufe {ex['level_idx']+1}/{ex['level_count']}</span>
            </div>
            <div style="font-size:11.5px;color:rgba(255,255,255,0.45);margin-bottom:6px">
                {ex['cue']} · Ziel: {ex['sets']} Sätze × {ex['target_reps']} {unit}</div>""",
                        unsafe_allow_html=True)

            ic1, ic2 = st.columns(2)
            with ic1:
                inputs[track] = {}
                inputs[track]['sets'] = st.number_input(
                    f"Sätze geschafft", min_value=0, max_value=ex['sets'] + 2, value=ex['sets'],
                    key=f"cal_sets_{track}")
            with ic2:
                inputs[track]['best'] = st.number_input(
                    f"Beste Leistung ({unit})", min_value=0, max_value=ex['target_reps'] * 3 + 10,
                    value=ex['target_reps'], key=f"cal_best_{track}")

        notes = st.text_input("Notiz (optional)", key="cal_notes", placeholder="z.B. heute schwer, wenig Schlaf")
        submitted = st.form_submit_button("✅ Training abschließen", use_container_width=True, type="primary")

    if submitted:
        level_ups = []
        clean_count = 0
        for track in today_tracks:
            result = log_cal_session(track, inputs[track]['sets'], inputs[track]['best'], notes)
            if result['clean']:
                clean_count += 1
            if result['leveled_up']:
                level_ups.append((track, result['new_level_name']))

        points = 40 * clean_count + 15 * (len(today_tracks) - clean_count)
        if entry_id:
            toggle_done(entry_id, True, points=points)
        else:
            sync_daily_training()
            entry_id, _ = get_todays_training_entry_id()
            if entry_id:
                toggle_done(entry_id, True, points=points)

        st.balloons()
        st.success(f"🎉 Training geloggt — {clean_count}/{len(today_tracks)} Übungen sauber geschafft, +{points} Punkte!")
        for track, new_name in level_ups:
            st.markdown(f"""<div style="background:linear-gradient(135deg,rgba(255,215,0,0.15),rgba(255,149,0,0.1));
                border:1px solid rgba(255,215,0,0.5);border-radius:12px;padding:14px 18px;margin-top:8px">
                <span style="font-size:18px">⬆️</span> <strong style="color:#ffd700">Level-Up: {CAL_TRACKS[track]['label']}!</strong><br>
                <span style="color:rgba(255,255,255,0.7);font-size:13px">Neue Übung freigeschaltet: <strong>{new_name}</strong></span>
            </div>""", unsafe_allow_html=True)
        time.sleep(0.3)
        st.rerun()

    st.markdown("---")

    # ── Progressionsleitern ──────────────────────────────────────
    st.markdown("### 🪜 Progressionsleitern")
    st.caption("Dein Weg von Stufe 1 bis zur Königsdisziplin — unendlich, jede Stufe ein Schritt weiter.")
    ladder_tracks = list(CAL_TRACKS.keys())
    for row_start in range(0, len(ladder_tracks), 3):
        cols = st.columns(3)
        for col, track in zip(cols, ladder_tracks[row_start:row_start + 3]):
            with col:
                st.markdown(_cal_track_ladder_html(track), unsafe_allow_html=True)

    st.markdown("---")

    # ── KI Trainingscoach ─────────────────────────────────────────
    st.markdown("### 🤖 KI Trainingscoach")
    api_key = get_setting('nvidia_api_key', '')
    if not api_key:
        st.info("Hinterlege einen NVIDIA API-Key in den Einstellungen, um den KI-Coach zu nutzen.")
    else:
        if st.button("🧠 Trainingsmuster analysieren", key="cal_coach_btn"):
            with st.spinner("Coach analysiert deine Trainingsdaten…"):
                st.session_state['_cal_coach_result'] = ki_training_coach(api_key)

        result = st.session_state.get('_cal_coach_result')
        if result:
            if result.get('error') == 'no_data':
                st.info("Noch keine Trainingsdaten — logge deine erste Einheit, dann kann der Coach Muster erkennen.")
            elif result.get('error'):
                st.error(f"Fehler: {result['error']}")
            else:
                weak = CAL_TRACKS.get(result.get('weak_track', ''), {}).get('label', '')
                strong = CAL_TRACKS.get(result.get('strong_track', ''), {}).get('label', '')
                st.markdown(f"""<div style="background:rgba(0,212,255,0.06);border:1px solid rgba(0,212,255,0.25);
                    border-radius:14px;padding:18px 20px">
                    <div style="font-size:15px;font-weight:800;color:#00d4ff;margin-bottom:10px">
                        🎙️ {result.get('headline','')}</div>
                    <div style="font-size:13px;color:rgba(255,255,255,0.8);margin-bottom:8px">
                        <strong>Muster erkannt:</strong> {result.get('pattern_detected','')}</div>
                    {f'<div style="font-size:12px;color:#f39c12;margin-bottom:6px">⚠️ Braucht Aufmerksamkeit: {weak}</div>' if weak else ''}
                    {f'<div style="font-size:12px;color:#2ecc71;margin-bottom:6px">📈 Bester Fortschritt: {strong}</div>' if strong else ''}
                    <div style="font-size:13px;color:rgba(255,255,255,0.8);margin-bottom:8px">
                        <strong>Nächster Fokus:</strong> {result.get('next_focus','')}</div>
                    <div style="font-size:12.5px;color:rgba(255,255,255,0.5);font-style:italic">
                        {result.get('motivation','')}</div>
                </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Konsistenz-Heatmap ─────────────────────────────────────
    st.markdown("### 📅 Konsistenz (letzte 84 Tage)")
    st.markdown(_cal_heatmap_html(), unsafe_allow_html=True)


# ========== SCHLAF & ROUTINEN SEITE ==========

def _sleep_ramp_hero_html(target):
    baseline_scale = _sleep_scale(target['baseline'])
    goal_scale = _sleep_scale(SLEEP_GOAL_BEDTIME)
    target_scale = _sleep_scale(target['target_time'])
    span = max(1, baseline_scale - goal_scale)
    pos_pct = max(0, min(100, (baseline_scale - target_scale) / span * 100))
    status = "🎉 Ziel erreicht!" if target['reached_goal'] else f"noch {target['days_to_goal']} Tage bis 00:00"

    return f"""<div style="background:linear-gradient(135deg,rgba(155,89,182,0.08),rgba(52,152,219,0.05));
  border:1px solid rgba(155,89,182,0.25);border-radius:16px;padding:20px 24px">
  <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:14px;flex-wrap:wrap;gap:10px">
    <div>
      <div style="font-size:11px;color:rgba(255,255,255,0.4);letter-spacing:1px;text-transform:uppercase">Heutige Ziel-Bettzeit</div>
      <div style="font-size:34px;font-weight:900;color:#a29bfe">{target['target_time']} Uhr</div>
    </div>
    <div style="text-align:right">
      <div style="font-size:11px;color:rgba(255,255,255,0.4);letter-spacing:1px;text-transform:uppercase">Aufstehen</div>
      <div style="font-size:20px;font-weight:800;color:#00d4ff">{SLEEP_GOAL_WAKETIME} Uhr · 8h Schlaf</div>
    </div>
  </div>
  <div style="position:relative;height:8px;background:rgba(255,255,255,0.08);border-radius:4px;margin-bottom:8px">
    <div style="position:absolute;left:0;top:0;height:100%;width:{pos_pct:.1f}%;
                background:linear-gradient(90deg,#9b59b6,#a29bfe);border-radius:4px"></div>
  </div>
  <div style="display:flex;justify-content:space-between;font-size:10px;color:rgba(255,255,255,0.35)">
    <span>Start: {target['baseline']} Uhr</span>
    <span style="font-weight:700;color:rgba(255,255,255,0.55)">{status}</span>
    <span>Ziel: 00:00 Uhr</span>
  </div>
</div>"""


def _routine_heatmap_html(routine_type, days=60):
    today_d = date.today()
    color = "#3498db" if routine_type == 'morning' else "#9b59b6"
    label = "Morgenroutine" if routine_type == 'morning' else "Abendroutine"
    adh_map = _routine_adherence_map(routine_type)

    def cell_color(frac):
        if not frac:
            return "rgba(255,255,255,0.05)"
        if frac >= 1:
            return color
        if frac >= 0.5:
            return f"{color}88"
        return f"{color}44"

    cells = ""
    for i in range(days - 1, -1, -1):
        d = today_d - timedelta(days=i)
        frac = adh_map.get(d.isoformat())
        tip = f"{d.strftime('%d.%m')}: {int((frac or 0) * 100)}%"
        cells += f'<div title="{tip}" style="width:14px;height:14px;background:{cell_color(frac)};border-radius:2px;flex-shrink:0"></div>'

    return f"""<div style="background:rgba(255,255,255,0.03);border-radius:12px;padding:14px 16px;
  border:1px solid rgba(255,255,255,0.07)">
  <div style="font-size:12px;font-weight:700;color:white;margin-bottom:8px">{label}</div>
  <div style="display:flex;flex-wrap:wrap;gap:3px;width:calc(14*(14px + 3px))">
    {cells}
  </div>
</div>"""


def render_morning_routine_checklist(today_str=None):
    """Eingebettete Morgenroutine-Checkliste, wiederverwendet in Planen (Schritt 0) und der Schlaf-Seite."""
    today_str = today_str or date.today().isoformat()
    checks_am = get_routine_checks(today_str, 'morning')
    for t in MORNING_ROUTINE_TASKS:
        cur = checks_am.get(t['key'], False)
        new = st.checkbox(f"{t['icon']} {t['label']}", value=cur, key=f"morning_chk_{t['key']}_{today_str}")
        if new != cur:
            set_routine_check(today_str, 'morning', t['key'], new)
            st.rerun()


def render_sleep_page():
    st.title("🌙 Schlaf & Routinen")
    st.caption("Die erste und letzte Stunde des Tages — die Basis für alles andere.")

    today_str = date.today().isoformat()
    target = get_sleep_target_bedtime()

    st.markdown(_sleep_ramp_hero_html(target), unsafe_allow_html=True)

    with st.expander("⚙️ Bettzeit-Rampe anpassen"):
        st.caption("Baseline = deine aktuelle, tatsächliche Bettzeit. Das Programm steigert sich von dort "
                   "täglich 10 Minuten Richtung 00:00.")
        bc1, bc2 = st.columns(2)
        with bc1:
            new_baseline = st.text_input("Baseline-Bettzeit (HH:MM)", value=target['baseline'],
                                         key="sleep_baseline_input")
        with bc2:
            st.write("")
            st.write("")
            if st.button("Rampe neu starten ab heute", key="sleep_restart_ramp"):
                try:
                    _sleep_scale(new_baseline)
                    set_setting('sleep_baseline_bedtime', new_baseline)
                    set_setting('sleep_program_start_date', today_str)
                    st.rerun()
                except Exception:
                    st.error("Bitte im Format HH:MM eingeben, z.B. 02:30")

    st.markdown("---")

    # ── Streaks ──────────────────────────────────────────────────
    morning_streak = get_routine_streak('morning')
    evening_streak = get_routine_streak('evening')
    s1, s2 = st.columns(2)
    with s1:
        st.markdown(f"""<div style="text-align:center;background:rgba(52,152,219,0.06);border-radius:14px;
            padding:14px;border:1px solid rgba(52,152,219,0.25)">
            <div style="font-size:24px">🌅</div>
            <div style="font-size:22px;font-weight:900;color:#3498db">{morning_streak['current']}</div>
            <div style="font-size:10px;color:rgba(255,255,255,0.4)">TAGE MORGENROUTINE VOLL</div>
        </div>""", unsafe_allow_html=True)
    with s2:
        st.markdown(f"""<div style="text-align:center;background:rgba(155,89,182,0.06);border-radius:14px;
            padding:14px;border:1px solid rgba(155,89,182,0.25)">
            <div style="font-size:24px">🌙</div>
            <div style="font-size:22px;font-weight:900;color:#9b59b6">{evening_streak['current']}</div>
            <div style="font-size:10px;color:rgba(255,255,255,0.4)">TAGE ABENDROUTINE VOLL</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Checklisten ──────────────────────────────────────────────
    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown("#### 🌅 Morgenroutine")
        render_morning_routine_checklist(today_str)
    with cc2:
        evening_start = None
        try:
            evening_start = _sleep_unscale(_sleep_scale(target['target_time']) - 60)
        except Exception:
            pass
        st.markdown(f"#### 🌙 Abendroutine{f' (ab {evening_start} Uhr)' if evening_start else ''}")
        checks_pm = get_routine_checks(today_str, 'evening')
        for t in EVENING_ROUTINE_TASKS:
            cur = checks_pm.get(t['key'], False)
            new = st.checkbox(f"{t['icon']} {t['label']}", value=cur, key=f"sleep_pm_{t['key']}_{today_str}")
            if new != cur:
                set_routine_check(today_str, 'evening', t['key'], new)
                st.rerun()

    st.markdown("---")

    # ── Schlaf-Eingabe ───────────────────────────────────────────
    st.markdown("#### 😴 Schlaf von letzter Nacht (aus Sleep Cycle)")
    existing = get_sleep_log(today_str)
    with st.form("sleep_log_form"):
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            quality = st.slider("Schlafqualität (%)", 0, 100,
                                value=existing['quality_pct'] if existing and existing['quality_pct'] is not None else 70)
        with sc2:
            bedtime_in = st.text_input("Bettzeit (HH:MM)",
                                       value=existing['bedtime'] if existing and existing['bedtime'] else "")
        with sc3:
            wake_in = st.text_input("Aufstehzeit (HH:MM)",
                                    value=existing['wake_time'] if existing and existing['wake_time'] else "")
        if st.form_submit_button("💾 Schlaf speichern"):
            log_sleep(today_str, quality, bedtime_in or None, wake_in or None)
            st.success("Gespeichert!")
            st.rerun()

    st.markdown("---")

    # ── Muster & Korrelation ───────────────────────────────────────
    st.markdown("### 🔍 Echte Muster aus deinen Daten")
    st.caption("Kein generischer Tipp — Vergleich deiner eigenen Tage mit vs. ohne vollständige Routine/guten Schlaf.")
    patterns = analyze_routine_patterns()

    def render_pattern_card(title, data, icon, unit="%", higher_is_better=True, fmt=lambda v: f"{v:.0f}"):
        if not data:
            st.info(f"{icon} **{title}**: Noch nicht genug Datenpunkte (mind. 3 Tage je Gruppe) — "
                    "sammle weiter Daten für eine zuverlässige Aussage.")
            return
        delta = data['hi_avg'] - data['lo_avg']
        better = (delta > 0) if higher_is_better else (delta < 0)
        col = "#2ecc71" if better else "#e74c3c"
        arrow = "↑" if delta > 0 else "↓"
        st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border-radius:12px;padding:14px 18px;
            border:1px solid rgba(255,255,255,0.08);margin-bottom:10px">
            <div style="font-size:12.5px;font-weight:700;color:white;margin-bottom:6px">{icon} {title}</div>
            <div style="display:flex;gap:24px;align-items:baseline;flex-wrap:wrap">
                <div><span style="font-size:20px;font-weight:900;color:{col}">{fmt(data['hi_avg'])}{unit}</span>
                     <span style="font-size:10px;color:rgba(255,255,255,0.4)"> (n={data['n_hi']})</span></div>
                <div style="color:rgba(255,255,255,0.3)">vs.</div>
                <div><span style="font-size:20px;font-weight:700;color:rgba(255,255,255,0.5)">{fmt(data['lo_avg'])}{unit}</span>
                     <span style="font-size:10px;color:rgba(255,255,255,0.4)"> (n={data['n_lo']})</span></div>
                <div style="font-size:13px;color:{col};font-weight:700">{arrow} {abs(delta):.0f}{unit}</div>
            </div>
        </div>""", unsafe_allow_html=True)

    render_pattern_card("Morgenroutine voll → Erledigungsquote selber Tag", patterns['morning_completion'], "🌅")
    render_pattern_card("Abendroutine voll → Erledigungsquote Folgetag", patterns['evening_next_completion'], "🌙")
    render_pattern_card("Schlafqualität ≥75% → Erledigungsquote selber Tag", patterns['sleep_quality'], "😴")

    speed = patterns['speed']
    if speed:
        delta = speed['lo_avg'] - speed['hi_avg']
        col = "#2ecc71" if delta > 0 else "#e74c3c"

        def fmt_min(m):
            h, mm = divmod(int(round(m)), 60)
            return f"{h:02d}:{mm:02d}"

        st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border-radius:12px;padding:14px 18px;
            border:1px solid rgba(255,255,255,0.08);margin-bottom:10px">
            <div style="font-size:12.5px;font-weight:700;color:white;margin-bottom:6px">
                ⚡ Morgenroutine voll → Zeit bis zur ersten erledigten Aufgabe</div>
            <div style="display:flex;gap:24px;align-items:baseline;flex-wrap:wrap">
                <div><span style="font-size:20px;font-weight:900;color:{col}">{fmt_min(speed['hi_avg'])} Uhr</span>
                     <span style="font-size:10px;color:rgba(255,255,255,0.4)"> (n={speed['n_hi']})</span></div>
                <div style="color:rgba(255,255,255,0.3)">vs.</div>
                <div><span style="font-size:20px;font-weight:700;color:rgba(255,255,255,0.5)">{fmt_min(speed['lo_avg'])} Uhr</span>
                     <span style="font-size:10px;color:rgba(255,255,255,0.4)"> (n={speed['n_lo']})</span></div>
            </div>
        </div>""", unsafe_allow_html=True)
    else:
        st.info("⚡ **Morgenroutine → Geschwindigkeit**: Noch nicht genug Datenpunkte.")

    st.markdown("---")

    # ── KI Schlafcoach ───────────────────────────────────────────
    st.markdown("### 🤖 KI Schlafcoach")
    api_key = get_setting('nvidia_api_key', '')
    if not api_key:
        st.info("Hinterlege einen NVIDIA API-Key in den Einstellungen, um den KI-Coach zu nutzen.")
    else:
        if st.button("🧠 Schlaf & Routinen analysieren", key="sleep_coach_btn"):
            with st.spinner("Coach analysiert deine Daten…"):
                st.session_state['_sleep_coach_result'] = ki_sleep_coach(api_key)
        result = st.session_state.get('_sleep_coach_result')
        if result:
            if result.get('error'):
                st.error(f"Fehler: {result['error']}")
            else:
                st.markdown(f"""<div style="background:rgba(155,89,182,0.06);border:1px solid rgba(155,89,182,0.25);
                    border-radius:14px;padding:18px 20px">
                    <div style="font-size:15px;font-weight:800;color:#a29bfe;margin-bottom:10px">
                        🎙️ {result.get('headline','')}</div>
                    <div style="font-size:13px;color:rgba(255,255,255,0.8);margin-bottom:8px">
                        <strong>Muster:</strong> {result.get('pattern_detected','')}</div>
                    <div style="font-size:13px;color:rgba(255,255,255,0.8);margin-bottom:8px">
                        <strong>Größter Hebel:</strong> {result.get('biggest_lever','')}</div>
                    <div style="font-size:13px;color:rgba(255,255,255,0.8);margin-bottom:8px">
                        <strong>Nächster Schritt:</strong> {result.get('next_step','')}</div>
                    <div style="font-size:12.5px;color:rgba(255,255,255,0.5);font-style:italic">
                        {result.get('motivation','')}</div>
                </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Konsistenz-Heatmaps ───────────────────────────────────────
    st.markdown("### 📅 Konsistenz (letzte 60 Tage)")
    hc1, hc2 = st.columns(2)
    with hc1:
        st.markdown(_routine_heatmap_html('morning'), unsafe_allow_html=True)
    with hc2:
        st.markdown(_routine_heatmap_html('evening'), unsafe_allow_html=True)


# ========== HAUSHALT SEITE ==========

def _household_score_hero_html(clean_score, wohlfuehl):
    def bar(label, value, color):
        return f"""<div style="flex:1;min-width:180px">
  <div style="display:flex;justify-content:space-between;margin-bottom:4px">
    <span style="font-size:11px;color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:1px">{label}</span>
    <span style="font-size:15px;font-weight:900;color:{color}">{value}</span>
  </div>
  <div style="height:10px;background:rgba(255,255,255,0.08);border-radius:5px">
    <div style="height:100%;width:{value}%;background:{color};border-radius:5px"></div>
  </div>
</div>"""

    return f"""<div style="background:linear-gradient(135deg,rgba(46,204,113,0.08),rgba(52,152,219,0.05));
  border:1px solid rgba(46,204,113,0.25);border-radius:16px;padding:20px 24px;
  display:flex;gap:24px;flex-wrap:wrap">
  {bar("🏡 Wohnung-Sauber-Score", clean_score, "#2ecc71")}
  {bar("😌 Wohlfühl-Index", wohlfuehl, "#00d4ff")}
</div>"""


def _household_status_badge(t):
    if t['overdue']:
        return f'<span style="color:#e74c3c;font-weight:700">🔴 überfällig (seit {t["days_since"]}d)</span>'
    if t['due']:
        return '<span style="color:#f39c12;font-weight:700">🟡 fällig</span>'
    if t['last_done']:
        return f'<span style="color:#2ecc71">✅ vor {t["days_since"]}d</span>'
    return '<span style="color:rgba(255,255,255,0.4)">— noch nie erledigt</span>'


def _render_household_section(status_all, frequency, today_str):
    tasks = [t for t in status_all if t['frequency'] == frequency]
    st.markdown(f"#### {HOUSEHOLD_FREQUENCY_LABELS[frequency]}")
    for t in tasks:
        c1, c2, c3 = st.columns([0.5, 0.28, 0.22])
        with c1:
            st.markdown(f"{t['icon']} **{t['label']}** <span style='font-size:10px;color:rgba(255,255,255,0.35)'>"
                        f"~{t['est_minutes']} Min</span>", unsafe_allow_html=True)
        with c2:
            st.markdown(_household_status_badge(t), unsafe_allow_html=True)
        with c3:
            if frequency == 'daily':
                done_today = t['last_done'] == today_str
                new = st.checkbox("erledigt", value=done_today, key=f"hh_{t['key']}_{today_str}",
                                  label_visibility="collapsed")
                if new != done_today:
                    if new:
                        log_household_task(t['key'], today_str)
                    else:
                        unlog_household_task(t['key'], today_str)
                    st.rerun()
            else:
                if st.button("✅ Erledigt", key=f"hh_btn_{t['key']}_{today_str}", use_container_width=True):
                    log_household_task(t['key'], today_str)
                    st.rerun()


def render_haushalt_page():
    st.title("🏡 Haushalt")
    st.caption("Wiederkehrende Aufgaben für ein Wohlfühl-Zuhause — als Pause zwischen Deep-Work-Sessions.")

    today_str = date.today().isoformat()
    status_all = get_household_status()
    clean_score = household_clean_score()
    wohlfuehl = household_wohlfuehl_index()

    st.markdown(_household_score_hero_html(clean_score, wohlfuehl), unsafe_allow_html=True)

    st.markdown("---")

    # ── Workload-bewusster Pausen-Vorschlag ───────────────────────
    suggestion = suggest_household_break_tasks()
    st.markdown("### ☕ Haushalts-Pausen heute")
    wl = suggestion['workload']
    st.caption(f"Zeitbudget heute: ~{suggestion['budget_minutes']} Min "
              f"({wl['undone_count']} offene Aufgaben, {wl['deadlines_today']} Deadlines heute)")
    if suggestion['tasks']:
        for t in suggestion['tasks']:
            st.markdown(f"- {t['icon']} **{t['label']}** (~{t['est_minutes']} Min)"
                       + (" 🔴 überfällig" if t['overdue'] else ""))
    else:
        st.success("Heute ist nichts dringend fällig — alles im grünen Bereich. 🎉")

    st.markdown("---")

    # ── Streak ─────────────────────────────────────────────────────
    streak = get_household_daily_streak()
    st.markdown(f"""<div style="text-align:center;background:rgba(46,204,113,0.06);border-radius:14px;
        padding:14px;border:1px solid rgba(46,204,113,0.25);margin-bottom:10px">
        <div style="font-size:24px">🏡</div>
        <div style="font-size:22px;font-weight:900;color:#2ecc71">{streak['current']}</div>
        <div style="font-size:10px;color:rgba(255,255,255,0.4)">TAGE TÄGLICHE HAUSHALTS-ROUTINE VOLL</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Aufgabenlisten nach Frequenz ───────────────────────────────
    _render_household_section(status_all, 'daily', today_str)
    st.markdown("")
    _render_household_section(status_all, 'weekly', today_str)
    st.markdown("")
    _render_household_section(status_all, 'monthly', today_str)

    st.markdown("---")

    # ── KI Haushaltscoach ────────────────────────────────────────
    st.markdown("### 🤖 KI Haushaltscoach")
    api_key = get_setting('nvidia_api_key', '')
    if not api_key:
        st.info("Hinterlege einen NVIDIA API-Key in den Einstellungen, um den KI-Coach zu nutzen.")
    else:
        if st.button("🧠 Haushalts-Pausen für heute empfehlen", key="haushalt_coach_btn"):
            with st.spinner("Coach plant deine Pausen…"):
                st.session_state['_haushalt_coach_result'] = ki_haushalt_coach(api_key)
        result = st.session_state.get('_haushalt_coach_result')
        if result:
            if result.get('error'):
                st.error(f"Fehler: {result['error']}")
            else:
                key_map = {t['key']: t for t in HOUSEHOLD_TASKS}
                rec_keys = result.get('recommended_keys') or []
                rec_str = ", ".join(
                    f"{key_map[k]['icon']} {key_map[k]['label']}" for k in rec_keys if k in key_map
                ) or "—"
                st.markdown(f"""<div style="background:rgba(46,204,113,0.06);border:1px solid rgba(46,204,113,0.25);
                    border-radius:14px;padding:18px 20px">
                    <div style="font-size:15px;font-weight:800;color:#2ecc71;margin-bottom:10px">
                        🎙️ {result.get('headline','')}</div>
                    <div style="font-size:13px;color:rgba(255,255,255,0.8);margin-bottom:8px">
                        <strong>Empfehlung:</strong> {rec_str}</div>
                    <div style="font-size:13px;color:rgba(255,255,255,0.8);margin-bottom:8px">
                        <strong>Begründung:</strong> {result.get('reasoning','')}</div>
                    <div style="font-size:12.5px;color:rgba(255,255,255,0.6);margin-bottom:8px">
                        <strong>Heute bewusst nicht:</strong> {result.get('skip_today','') or '—'}</div>
                    <div style="font-size:12.5px;color:rgba(255,255,255,0.5);font-style:italic">
                        {result.get('motivation','')}</div>
                </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Konsistenz-Heatmap ─────────────────────────────────────────
    st.markdown("### 📅 Konsistenz (letzte 60 Tage)")
    st.markdown(_household_heatmap_html(), unsafe_allow_html=True)


# ========== MAIN ==========

def main():
    st.set_page_config(page_title="Kaizen — ADHS-optimiert", layout="wide")

    # Restore from cloud backup if DB missing / empty (Streamlit Cloud redeploy)
    if 'db_restore_checked' not in st.session_state:
        st.session_state['db_restore_checked'] = True
        import os as _os
        if not _os.path.exists(DB_PATH) or _os.path.getsize(DB_PATH) < 1024:
            auto_restore_db()

    init_db()

    if 'page' not in st.session_state:
        st.session_state.page = 'Start'

    sync_recurring_tasks()
    sync_project_tasks()
    sync_daily_training()

    # Fire pending backup (non-blocking, background)
    if st.session_state.pop('_backup_pending', False):
        import threading as _t
        _t.Thread(target=auto_backup_db, daemon=True).start()

    if 'selected_project' not in st.session_state:
        st.session_state.selected_project = None

    PAGES = ["Start", "Planen", "Tagesfokus", "Training", "Schlaf", "Haushalt", "Projekte", "Alle Einträge", "Routinen", "Habits", "Charakter", "Season Pass", "KI Coach", "Statistiken", "Einstellungen"]
    if st.session_state.page not in PAGES:
        st.session_state.page = "Start"

    # ── Spontane-Gedanken-Bubble (permanent, auf jeder Seite) ──
    _render_spontan_bubble()

    # ── Brand Header ──────────────────────────────────────────
    st.sidebar.markdown("""
<div style="text-align:center;padding:18px 0 10px 0">
  <div style="font-size:30px;margin-bottom:6px">⛰️</div>
  <div style="font-size:17px;font-weight:900;letter-spacing:4px;
              background:linear-gradient(135deg,#00d4ff 0%,#a29bfe 100%);
              -webkit-background-clip:text;-webkit-text-fill-color:transparent;
              background-clip:text;display:inline-block">KAIZEN</div>
  <div style="font-size:9px;color:rgba(255,255,255,0.25);letter-spacing:2px;
              text-transform:uppercase;margin-top:3px">Daily Flow System</div>
</div>""", unsafe_allow_html=True)

    # ── Navigation ────────────────────────────────────────────
    _PAGE_ICONS = {
        "Start": "🏠", "Planen": "📋", "Tagesfokus": "🎯", "Training": "🏋️", "Schlaf": "🌙", "Haushalt": "🏡",
        "Projekte": "📁", "Alle Einträge": "📅", "Routinen": "🔄",
        "Habits": "✅", "Charakter": "🧙", "Season Pass": "🎖️",
        "KI Coach": "🤖", "Statistiken": "📊", "Einstellungen": "⚙️",
    }
    page = st.sidebar.selectbox(
        "Navigation", PAGES,
        index=PAGES.index(st.session_state.page),
        format_func=lambda p: f"{_PAGE_ICONS.get(p, '·')}  {p}",
        label_visibility="collapsed"
    )
    st.session_state.page = page

    # ── Fokus-Modus ───────────────────────────────────────────
    if st.session_state.get('focus_task_id') and st.session_state.get('focus_phase'):
        _render_focus_mode()
        level, progress, goal = get_level_and_progress()
        st.sidebar.markdown(f"""
<div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:10px 12px;
            border:1px solid rgba(255,255,255,0.1);text-align:center">
  <div style="font-size:13px;color:rgba(255,255,255,0.6)">Level {level}</div>
  <div style="font-size:18px;font-weight:800;color:#00d4ff">{total_points()} Pts</div>
</div>""", unsafe_allow_html=True)
        return

    if page == "Start":
        render_start_page()
    elif page == "Planen":
        render_planen_page()
    elif page == "Tagesfokus":
        render_tagesfokus_page()
    elif page == "Training":
        render_training_page()
    elif page == "Schlaf":
        render_sleep_page()
    elif page == "Haushalt":
        render_haushalt_page()
    elif page == "Projekte":
        render_projekte_page()
    elif page == "Alle Einträge":
        render_alle_eintraege_page()
    elif page == "Routinen":
        render_routinen_page()
    elif page == "Habits":
        render_habit_tracker_page()
    elif page == "Charakter":
        render_character_page()
    elif page == "Season Pass":
        render_season_pass_page()
    elif page == "KI Coach":
        render_ki_coach_page()
    elif page == "Statistiken":
        render_statistics_page()
    elif page == "Einstellungen":
        render_settings_page()

    # ── Charakter / Score Card ─────────────────────────────────
    rpg_char = get_character()
    if rpg_char and rpg_char.get('class_id'):
        c_level, c_xp, c_xp_next = compute_level(rpg_char['total_xp'])
        c_pct = int(c_xp / c_xp_next * 100) if c_xp_next > 0 else 0
        c_ci = CLASS_INFO.get(rpg_char.get('class_id', ''), {})
        c_col = c_ci.get('color', '#00d4ff')
        c_body = _get_char_body(c_level, rpg_char.get('class_id', ''), rpg_char.get('equipped_body', ''))
        st.sidebar.markdown(f"""
<div style="background:rgba(255,255,255,0.05);border-radius:12px;
  padding:10px 12px;margin:8px 0;border:1px solid rgba(255,255,255,0.1)">
  <div style="display:flex;align-items:center;gap:10px">
    <div style="font-size:32px;filter:drop-shadow(0 0 8px {c_col})">{c_body}</div>
    <div style="flex:1;min-width:0">
      <div style="font-weight:700;color:white;font-size:13px;white-space:nowrap;
                  overflow:hidden;text-overflow:ellipsis">{rpg_char['name']}</div>
      <div style="font-size:10px;color:{c_col};font-weight:600;margin-top:1px">
        Level {c_level} · 💰 {rpg_char['coins']}</div>
      <div style="background:rgba(255,255,255,0.1);border-radius:4px;height:4px;
                  margin-top:5px;overflow:hidden">
        <div style="width:{c_pct}%;height:100%;border-radius:4px;background:{c_col};
                    box-shadow:0 0 6px {c_col}88"></div>
      </div>
      <div style="font-size:9px;color:rgba(255,255,255,0.28);margin-top:2px">
        {c_xp}/{c_xp_next} XP</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)
    else:
        level, progress, goal = get_level_and_progress()
        pct_lvl = int(progress / goal * 100) if goal > 0 else 0
        st.sidebar.markdown(f"""
<div style="background:rgba(255,255,255,0.05);border-radius:12px;
  padding:10px 12px;margin:8px 0;border:1px solid rgba(255,255,255,0.1)">
  <div style="font-size:11px;color:rgba(255,255,255,0.4);letter-spacing:1px">LEVEL {level}</div>
  <div style="font-size:20px;font-weight:800;color:#00d4ff">{total_points()} Pts</div>
  <div style="background:rgba(255,255,255,0.1);border-radius:4px;height:4px;margin-top:6px;overflow:hidden">
    <div style="width:{pct_lvl}%;height:100%;background:#00d4ff;border-radius:4px"></div>
  </div>
</div>""", unsafe_allow_html=True)

    # ── Heute Schnellübersicht ─────────────────────────────────
    _today_str = date.today().isoformat()
    _conn = sqlite3.connect(DB_PATH)
    _cc = _conn.cursor()
    _cc.execute("SELECT COUNT(*), COALESCE(SUM(done),0) FROM entries WHERE entry_date=?", (_today_str,))
    _t_total, _t_done = _cc.fetchone()
    _t_done = _t_done or 0
    _cc.execute("SELECT COALESCE(SUM(points),0) FROM entries WHERE entry_date=? AND done=1", (_today_str,))
    _pts_today = _cc.fetchone()[0] or 0
    _conn.close()
    _pct_day = int(_t_done / _t_total * 100) if _t_total else 0
    _bar_col = "#e74c3c" if _pct_day < 30 else "#f39c12" if _pct_day < 65 else "#2ecc71"
    st.sidebar.markdown(f"""
<div style="background:rgba(255,255,255,0.03);border-radius:10px;padding:9px 12px;
            margin-bottom:6px;border:1px solid rgba(255,255,255,0.06)">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px">
    <span style="font-size:9px;color:rgba(255,255,255,0.4);font-weight:700;
                 letter-spacing:1.5px;text-transform:uppercase">Heute</span>
    <span style="font-size:11px;color:#ffd700;font-weight:700">⚡ {_pts_today} Pts</span>
  </div>
  <div style="background:rgba(255,255,255,0.08);border-radius:3px;height:3px;overflow:hidden">
    <div style="width:{_pct_day}%;height:100%;background:{_bar_col};border-radius:3px"></div>
  </div>
  <div style="font-size:9px;color:rgba(255,255,255,0.3);margin-top:3px">
    {_t_done} / {_t_total} Aufgaben · {_pct_day}%</div>
</div>""", unsafe_allow_html=True)

    st.sidebar.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── Einstellungen & Tools ──────────────────────────────────
    with st.sidebar.expander("⚙️  Punkte & Level"):
        pts_input = st.number_input("Punkte pro Aufgabe",
                                     value=int(get_setting('points_per_task') or POINTS_PER_TASK), min_value=1)
        lvl_input = st.number_input("Punkte pro Level",
                                     value=int(get_setting('level_step') or LEVEL_STEP), min_value=10)
        _c1, _c2 = st.columns(2)
        with _c1:
            if st.button("Speichern", use_container_width=True):
                set_setting('points_per_task', pts_input)
                set_setting('level_step', lvl_input)
                st.success("✓")
        with _c2:
            if st.button("Reset", use_container_width=True):
                set_setting('points_per_task', POINTS_PER_TASK)
                set_setting('level_step', LEVEL_STEP)
                st.success("✓")

    with st.sidebar.expander("☁️  Export / Sync"):
        if st.checkbox("GitHub Gist"):
            token = st.text_input("Token", type="password")
            gist_id = st.text_input("Gist ID (leer → neu)")
            if st.button("Exportieren", use_container_width=True):
                conn2 = sqlite3.connect(DB_PATH)
                c2 = conn2.cursor()
                c2.execute('SELECT id, entry_type, content, tags, priority, estimate_minutes, points, created_at, entry_date, done, completed_at, elapsed_seconds, deadline FROM entries')
                allrows = c2.fetchall()
                conn2.close()
                payload = json.dumps([dict(id=r[0], type=r[1], content=r[2], tags=r[3],
                                            priority=r[4], estimate=r[5], points=r[6],
                                            created_at=r[7], entry_date=r[8], done=r[9],
                                            completed_at=r[10], elapsed_seconds=r[11],
                                            deadline=r[12]) for r in allrows], ensure_ascii=False)
                if token and gist_id:
                    status, _ = gist_save(token, gist_id, payload)
                    st.write(f"Status: {status}")
                elif token:
                    status, resp = gist_create(token, payload)
                    st.write("OK:", resp.get('html_url') if status == 201 else status)
                else:
                    st.download_button("Download JSON", data=payload,
                                        file_name=f"kaizen_{date.today().isoformat()}.json")

    with st.sidebar.expander("🗄️  Datenverwaltung"):
        _db1, _db2 = st.columns(2)
        with _db1:
            if st.button("Beispiele +", use_container_width=True):
                insert_sample_data()
                st.success("✓")
        with _db2:
            if st.button("Beispiele −", use_container_width=True):
                delete_sample_data()
                st.success("✓")
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        _del_confirm = st.text_input("⚠️ Alle Daten löschen — tippe DELETE")
        if st.button("Alles löschen", type="secondary", use_container_width=True) and _del_confirm == "DELETE":
            delete_all_data()
            st.success("Gelöscht.")

    # ── Footer ────────────────────────────────────────────────
    st.sidebar.markdown("""
<div style="margin-top:16px;padding:10px 0;border-top:1px solid rgba(255,255,255,0.07);
            text-align:center">
  <div style="font-size:9px;color:rgba(255,255,255,0.2);letter-spacing:1px">
    一日一善 · jeden Tag ein bisschen besser</div>
</div>""", unsafe_allow_html=True)


if __name__ == '__main__':
    main()
