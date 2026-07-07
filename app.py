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
HOUSEHOLD_FREQUENCY_DAYS = {'daily': 1, 'weekly': 7, 'monthly': 30, 'custom': None}
HOUSEHOLD_FREQUENCY_LABELS = {
    'daily':   '📅 Täglich',
    'weekly':  '🗓️ Wöchentlich',
    'monthly': '📆 Monatlich',
    'custom':  '🔧 Eigener Rhythmus',
}

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
    CREATE TABLE IF NOT EXISTS focus_blocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_id INTEGER,
        task_name TEXT,
        block_date TEXT,
        started_at TEXT,
        ended_at TEXT,
        duration_seconds INTEGER DEFAULT 0,
        round_number INTEGER DEFAULT 1,
        steps_completed INTEGER DEFAULT 0,
        total_steps INTEGER DEFAULT 0
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
    c.execute('''
    CREATE TABLE IF NOT EXISTS daily_training_exercises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_date TEXT NOT NULL,
        track TEXT NOT NULL,
        exercise_name TEXT NOT NULL,
        sets INTEGER DEFAULT 3,
        reps INTEGER DEFAULT 0,
        hold_seconds INTEGER DEFAULT 0,
        cue TEXT DEFAULT '',
        why TEXT DEFAULT '',
        difficulty INTEGER DEFAULT 5,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(plan_date, track, exercise_name)
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
    c.execute('''
    CREATE TABLE IF NOT EXISTS custom_household_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_key TEXT UNIQUE NOT NULL,
        icon TEXT DEFAULT '🏡',
        label TEXT NOT NULL,
        frequency TEXT DEFAULT 'weekly',
        est_minutes INTEGER DEFAULT 15,
        interval_days INTEGER DEFAULT 7,
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
    # ─── Tagebuch / Tagesreflexion ───────────────────────────────
    c.execute('''
    CREATE TABLE IF NOT EXISTS journal_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date TEXT NOT NULL UNIQUE,
        content TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    ''')
    # Migration: roter_faden column for projects
    try:
        c.execute("ALTER TABLE projects ADD COLUMN roter_faden TEXT DEFAULT ''")
    except Exception:
        pass

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


def delete_entry(entry_id):
    conn = sqlite3.connect(DB_PATH)
    # If this is a project-task entry, reschedule the underlying project_tasks
    # row to tomorrow; without this, sync_project_tasks() would immediately
    # re-add the entry on the next rerun.
    row = conn.execute("SELECT content, tags FROM entries WHERE id=?", (entry_id,)).fetchone()
    if row and row[1] and 'projekt' in row[1]:
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        conn.execute(
            "UPDATE project_tasks SET scheduled_date=? WHERE content=? AND done=0",
            (tomorrow, row[0])
        )
    conn.execute("DELETE FROM task_steps WHERE entry_id=?", (entry_id,))
    conn.execute("DELETE FROM entries WHERE id=?", (entry_id,))
    conn.commit()
    conn.close()
    _schedule_backup()


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


def log_focus_block(entry_id, task_name, started_at, ended_at, duration_secs, round_num, steps_completed, total_steps):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO focus_blocks
            (entry_id, task_name, block_date, started_at, ended_at,
             duration_seconds, round_number, steps_completed, total_steps)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (entry_id, task_name, date.today().isoformat(),
          started_at, ended_at, int(duration_secs), round_num,
          steps_completed, total_steps))
    conn.commit()
    conn.close()


def get_focus_blocks(days=30):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT block_date, task_name, duration_seconds, round_number,
               steps_completed, total_steps, started_at
        FROM focus_blocks
        WHERE block_date >= date('now',?) ORDER BY started_at DESC
    """, (f'-{days} days',)).fetchall()
    conn.close()
    return [{'date': r[0], 'task': r[1], 'secs': r[2], 'round': r[3],
             'steps_done': r[4], 'steps_total': r[5], 'started': r[6]} for r in rows]


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
        # Propagate to project_tasks if this is a project entry, so it won't re-appear
        row_tags = c.execute("SELECT content, tags FROM entries WHERE id=?", (entry_id,)).fetchone()
        if row_tags and row_tags[1] and 'projekt' in row_tags[1]:
            c.execute("UPDATE project_tasks SET done=1, completed_at=? WHERE content=? AND done=0",
                      (now, row_tags[0]))
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
    c.execute('''SELECT id, name, description, deadline, color, active, created_at, daily_minutes,
                        COALESCE(roter_faden,'')
                 FROM projects ORDER BY created_at DESC''')
    rows = c.fetchall()
    conn.close()
    return rows


def add_project(name, description, deadline, color, daily_minutes, roter_faden=''):
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO projects (name, description, deadline, color, active, created_at, daily_minutes, roter_faden)
                 VALUES (?,?,?,?,1,?,?,?)''',
              (name, description, deadline, color, now, daily_minutes, roter_faden))
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
    """Zieht GENAU EINE Aufgabe pro Projekt in den heutigen Tag — nie mehr, kein Flooding.
    Nicht erledigte Tasks von gestern werden in den nächsten Tag geschoben, kein neuer Task geholt."""
    today_str = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    projects = c.execute("SELECT id, name FROM projects WHERE active=1").fetchall()

    for proj_id, proj_name in projects:
        # 1. Bereits ein aktiver (undone) Task für heute in project_tasks?
        today_task = c.execute(
            "SELECT id, content, estimate_minutes FROM project_tasks WHERE project_id=? AND scheduled_date=? AND done=0",
            (proj_id, today_str)
        ).fetchone()

        if not today_task:
            # 2. Gibt es einen überfälligen undone Task? → auf heute verschieben (nicht duplizieren)
            overdue = c.execute(
                """SELECT id, content, estimate_minutes FROM project_tasks
                   WHERE project_id=? AND done=0 AND scheduled_date IS NOT NULL AND scheduled_date != '' AND scheduled_date < ?
                   ORDER BY scheduled_date, order_index LIMIT 1""",
                (proj_id, today_str)
            ).fetchone()

            if overdue:
                c.execute("UPDATE project_tasks SET scheduled_date=? WHERE id=?", (today_str, overdue[0]))
                today_task = overdue
            else:
                # 3. Nächster ungeschedulter undone Task → für heute einplanen
                next_task = c.execute(
                    """SELECT id, content, estimate_minutes FROM project_tasks
                       WHERE project_id=? AND done=0 AND (scheduled_date IS NULL OR scheduled_date='')
                       ORDER BY order_index, id LIMIT 1""",
                    (proj_id,)
                ).fetchone()
                if next_task:
                    c.execute("UPDATE project_tasks SET scheduled_date=? WHERE id=?", (today_str, next_task[0]))
                    today_task = next_task

        if not today_task:
            continue  # Alle Tasks erledigt

        task_id, content, estimate = today_task

        # 4. In entries eintragen — aber nur wenn noch nicht vorhanden (kein Duplicate)
        already = c.execute(
            "SELECT COUNT(*) FROM entries WHERE entry_date=? AND content=? AND tags LIKE '%projekt%'",
            (today_str, content)
        ).fetchone()[0]

        if already == 0:
            now = datetime.utcnow().isoformat()
            c.execute(
                """INSERT INTO entries (entry_type, content, tags, estimate_minutes, points, created_at, entry_date, last_modified)
                   VALUES (?,?,?,?,0,?,?,?)""",
                ('brain', content, f'projekt,{proj_name}', estimate or 30, now, today_str, now)
            )

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


def get_stored_training_plan():
    """Liest den gespeicherten Trainingsplan für heute aus settings."""
    raw = get_setting(f"training_plan_{date.today().isoformat()}")
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    return None


def save_training_plan(plan):
    """Speichert den Trainingsplan für heute in settings."""
    set_setting(f"training_plan_{date.today().isoformat()}", json.dumps(plan))


def get_todays_auto_plan():
    """Rotation-Plan ohne KI: wählt Tracks basierend auf Erholungszeiten."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT track, MAX(session_date) FROM cal_sessions GROUP BY track"
    ).fetchall()
    conn.close()

    today = date.today()
    last_date_map = {t: ld for t, ld in rows if ld}

    def days_since(track):
        if track not in last_date_map:
            return 999
        return (today - date.fromisoformat(last_date_map[track])).days

    MIN_REST = {'push': 2, 'pull': 2, 'legs': 2, 'core': 1,
                'skill_handstand': 1, 'skill_muscleup': 1}

    ready = {t: days_since(t) for t in CAL_TRACKS if days_since(t) >= MIN_REST.get(t, 2)}

    if not ready:
        return {
            'tracks': [], 'rest_day': True, 'source': 'auto',
            'rationale': 'Alle Muskelgruppen brauchen noch Erholung — Ruhetag empfohlen.'
        }

    muscle_ready = sorted(
        [t for t in ['push', 'pull', 'legs'] if t in ready],
        key=lambda t: -ready[t]
    )
    picked = muscle_ready[:2]

    if 'core' in ready:
        picked.append('core')

    skill_ready = sorted(
        [t for t in ['skill_handstand', 'skill_muscleup'] if t in ready],
        key=lambda t: -ready[t]
    )
    if skill_ready:
        picked.append(skill_ready[0])

    if not picked:
        return {
            'tracks': [], 'rest_day': True, 'source': 'auto',
            'rationale': 'Nichts bereit — Ruhetag empfohlen.'
        }

    parts = [
        f"{CAL_TRACKS[t]['label']} ({ready[t]}T Pause)" if ready[t] < 999
        else f"{CAL_TRACKS[t]['label']} (erstes Mal)"
        for t in picked
    ]
    return {
        'tracks': picked,
        'rest_day': False,
        'source': 'auto',
        'rationale': 'Auto-Rotation: ' + ', '.join(parts)
    }


def todays_cal_tracks():
    # KI-generierte Übungen haben Priorität
    ki_tracks = get_daily_exercise_tracks()
    if ki_tracks:
        return ki_tracks
    plan = get_stored_training_plan()
    if plan is not None:
        return plan.get('tracks', [])
    auto = get_todays_auto_plan()
    save_training_plan(auto)
    return auto.get('tracks', [])


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


# ── KI Daily Exercise Plan — DB Helpers ─────────────────────────

def save_daily_exercises(date_str, tracks_data, meta=None):
    """Speichert KI-generierte Übungen. tracks_data = [{'track':str, 'exercises':[...]}]"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM daily_training_exercises WHERE plan_date=?", (date_str,))
    sort_order = 0
    for td in tracks_data:
        track = td.get('track', '')
        for ex in td.get('exercises', []):
            conn.execute("""
                INSERT OR REPLACE INTO daily_training_exercises
                (plan_date, track, exercise_name, sets, reps, hold_seconds, cue, why, difficulty, sort_order)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (date_str, track, ex.get('name', ''), int(ex.get('sets', 3)),
                  int(ex.get('reps', 0)), int(ex.get('hold_seconds', 0)),
                  ex.get('cue', ''), ex.get('why', ''), int(ex.get('difficulty', 5)), sort_order))
            sort_order += 1
    conn.commit()
    conn.close()
    if meta:
        save_training_plan({**meta, 'source': 'ki', 'rest_day': False,
                            'tracks': [td['track'] for td in tracks_data if td.get('exercises')]})


def get_daily_exercises(date_str=None):
    """Gibt die KI-generierten Übungen des Tages zurück: {track: [exercise_dicts]}"""
    date_str = date_str or date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT id, track, exercise_name, sets, reps, hold_seconds, cue, why, difficulty
        FROM daily_training_exercises WHERE plan_date=? ORDER BY sort_order, id
    """, (date_str,)).fetchall()
    conn.close()
    result = {}
    for row in rows:
        track = row[1]
        result.setdefault(track, []).append({
            'id': row[0], 'name': row[2], 'sets': row[3], 'reps': row[4],
            'hold_seconds': row[5], 'cue': row[6], 'why': row[7], 'difficulty': row[8]
        })
    return result


def get_daily_exercise_tracks(date_str=None):
    """Track-Keys für den heutigen KI-Plan."""
    date_str = date_str or date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT DISTINCT track FROM daily_training_exercises WHERE plan_date=? ORDER BY rowid",
        (date_str,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def log_ki_exercise(date_str, track, exercise_name, sets_done, reps_done,
                    target_sets, target_reps, is_hold=False, notes=''):
    """Loggt eine KI-geplante Übung in cal_sessions."""
    clean = sets_done >= target_sets and reps_done >= target_reps
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO cal_sessions
        (session_date, track, exercise_name, sets_completed, target_sets,
         best_reps, target_reps, is_hold, clean, notes, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (date_str, track, exercise_name, sets_done, target_sets,
          reps_done, target_reps, int(is_hold), int(clean), notes, now))
    conn.commit()
    conn.close()
    _schedule_backup()
    return clean


def sync_daily_training():
    """Erstellt das heutige Trainings-Highlight im Kalender (einmal pro Tag, idempotent)."""
    today_str = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM entries WHERE entry_date=? AND tags LIKE '%training%'", (today_str,))
    if c.fetchone()[0] == 0:
        tracks = todays_cal_tracks()
        if tracks:  # kein Eintrag an Ruhetagen
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


def get_custom_household_tasks():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT task_key, icon, label, frequency, est_minutes, interval_days FROM custom_household_tasks WHERE active=1"
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        freq = r[3]
        interval = r[5] if freq == 'custom' else HOUSEHOLD_FREQUENCY_DAYS.get(freq, 7)
        result.append({
            'key': r[0], 'icon': r[1], 'label': r[2],
            'frequency': freq, 'est_minutes': r[4],
            'interval_days': interval, 'is_custom': True
        })
    return result


def get_all_household_tasks():
    """HOUSEHOLD_TASKS (built-in, ohne versteckte) + custom DB tasks."""
    hidden = get_hidden_builtin_keys()
    built_in = []
    for t in HOUSEHOLD_TASKS:
        if t['key'] in hidden:
            continue
        t2 = dict(t)
        t2['interval_days'] = HOUSEHOLD_FREQUENCY_DAYS.get(t['frequency'], 7)
        t2['is_custom'] = False
        built_in.append(t2)
    return built_in + get_custom_household_tasks()


def add_custom_household_task(label, icon, frequency, est_minutes, interval_days=7):
    key = f"custom_{label.lower().replace(' ','_')[:30]}_{int(datetime.utcnow().timestamp())}"
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR IGNORE INTO custom_household_tasks (task_key, icon, label, frequency, est_minutes, interval_days) VALUES (?,?,?,?,?,?)",
        (key, icon, label, frequency, est_minutes, interval_days)
    )
    conn.commit()
    conn.close()


def delete_custom_household_task(task_key):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE custom_household_tasks SET active=0 WHERE task_key=?", (task_key,))
    conn.commit()
    conn.close()


def hide_builtin_household_task(task_key):
    """Blendet eine eingebaute Haushaltsaufgabe aus (reversibel)."""
    raw = get_setting('household_hidden_builtin') or '[]'
    try:
        hidden = set(json.loads(raw))
    except Exception:
        hidden = set()
    hidden.add(task_key)
    set_setting('household_hidden_builtin', json.dumps(list(hidden)))


def show_builtin_household_task(task_key):
    """Macht eine ausgeblendete built-in Aufgabe wieder sichtbar."""
    raw = get_setting('household_hidden_builtin') or '[]'
    try:
        hidden = set(json.loads(raw))
    except Exception:
        hidden = set()
    hidden.discard(task_key)
    set_setting('household_hidden_builtin', json.dumps(list(hidden)))


def get_hidden_builtin_keys():
    raw = get_setting('household_hidden_builtin') or '[]'
    try:
        return set(json.loads(raw))
    except Exception:
        return set()


def sync_household_to_entries():
    """Zieht fällige Haushalt-Tasks smart in die To-Do-Liste.
    Läuft exakt EINMAL pro Tag — gelöschte Tasks kommen nicht zurück, keine neuen werden nachgefüllt."""
    today_str = date.today().isoformat()
    today_d   = date.today()

    # ── Einmal-pro-Tag-Guard: wenn heute schon gelaufen → sofort raus ──
    done_key = f"household_sync_done_{today_str}"
    if get_setting(done_key):
        return

    sync_key    = f"household_synced_{today_str}"
    synced_raw  = get_setting(sync_key)
    already_synced = set(json.loads(synced_raw)) if synced_raw else set()

    conn = sqlite3.connect(DB_PATH)

    # ── Tages-Auslastung messen (ohne Haushalt-Tasks) ──────────────
    task_count = conn.execute(
        "SELECT COUNT(*) FROM entries WHERE entry_date=? AND done=0 AND tags NOT LIKE '%haushalt%'",
        (today_str,)
    ).fetchone()[0]
    total_est = conn.execute(
        "SELECT COALESCE(SUM(estimate_minutes),0) FROM entries WHERE entry_date=? AND done=0 AND tags NOT LIKE '%haushalt%'",
        (today_str,)
    ).fetchone()[0]

    # ── Schwellenwerte ──────────────────────────────────────────────
    if task_count >= 10 or total_est >= 300:
        conn.close()
        return
    elif task_count >= 6 or total_est >= 150:
        max_tasks, max_minutes = 1, 10
    elif task_count >= 3 or total_est >= 60:
        max_tasks, max_minutes = 2, 20
    else:
        max_tasks, max_minutes = 3, 999

    # ── Welche Haushalt-Tasks sind GERADE in entries (nicht gelöscht) ──
    existing_now = {r[0] for r in conn.execute(
        "SELECT content FROM entries WHERE entry_date=? AND tags LIKE '%haushalt%'",
        (today_str,)
    ).fetchall()}

    # ── Letzte Erledigungen ────────────────────────────────────────
    last_done_map = {r[0]: r[1] for r in conn.execute(
        "SELECT task_key, MAX(log_date) FROM household_log GROUP BY task_key"
    ).fetchall()}

    conn.close()

    all_tasks = get_all_household_tasks()
    due_tasks = []
    for t in all_tasks:
        interval = t.get('interval_days') or HOUSEHOLD_FREQUENCY_DAYS.get(t['frequency'], 7) or 7
        last = last_done_map.get(t['key'])
        days_since = (today_d - date.fromisoformat(last)).days if last else interval + 1

        if (days_since >= interval
                and t['label'] not in existing_now      # nicht schon in entries
                and t['label'] not in already_synced    # nicht schon mal heute gesynct (= user hat es gelöscht → nicht wiederholen)
                and t['est_minutes'] <= max_minutes):
            due_tasks.append((max(0, days_since - interval), t))

    due_tasks.sort(key=lambda x: x[0], reverse=True)

    newly_added = []
    if due_tasks:
        conn2 = sqlite3.connect(DB_PATH)
        for _, t in due_tasks[:max_tasks]:
            conn2.execute("""
                INSERT INTO entries (entry_type, content, tags, estimate_minutes, entry_date, done)
                VALUES ('micro', ?, 'haushalt', ?, ?, 0)
            """, (t['label'], t['est_minutes'], today_str))
            newly_added.append(t['label'])
        conn2.commit()
        conn2.close()

    # ── Sync-Tracking aktualisieren + Done-Guard setzen ────────────
    if newly_added:
        updated = already_synced | set(newly_added)
        set_setting(sync_key, json.dumps(list(updated), ensure_ascii=False))

    # Guard: sync läuft heute nicht nochmal (verhindert Nachfüllen wenn Tasks gelöscht werden)
    set_setting(done_key, "1")


def get_household_status():
    """Für jede Haushaltsaufgabe: zuletzt erledigt, Tage seitdem, fällig/überfällig, Dringlichkeit."""
    today = date.today()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT task_key, MAX(log_date) FROM household_log GROUP BY task_key").fetchall()
    conn.close()
    last_done_map = {k: v for k, v in rows}

    out = []
    for t in get_all_household_tasks():
        last_done = last_done_map.get(t['key'])
        interval = t.get('interval_days') or HOUSEHOLD_FREQUENCY_DAYS.get(t['frequency'], 7) or 7
        if last_done:
            days_since = (today - date.fromisoformat(last_done)).days
        else:
            days_since = interval * 3
        due     = days_since >= interval
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
        interval = t.get('interval_days') or HOUSEHOLD_FREQUENCY_DAYS.get(t['frequency'], 7) or 7
        freshness = max(0.0, 1 - t['days_since'] / (interval * 1.5))
        freshness_vals.append(freshness)
    return int(round(sum(freshness_vals) / len(freshness_vals) * 100))


def get_household_daily_streak():
    daily_keys = [t['key'] for t in get_all_household_tasks() if t['frequency'] == 'daily']
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


# ========== JOURNAL / TAGESREFLEXION ==========

def save_journal_entry(content):
    now = datetime.utcnow().isoformat()
    today_str = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        INSERT INTO journal_entries (entry_date, content, created_at, updated_at)
        VALUES (?,?,?,?)
        ON CONFLICT(entry_date) DO UPDATE SET content=excluded.content, updated_at=excluded.updated_at
    ''', (today_str, content.strip(), now, now))
    conn.commit()
    conn.close()
    _schedule_backup()


def get_journal_entry(date_str=None):
    date_str = date_str or date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT content FROM journal_entries WHERE entry_date=?", (date_str,)).fetchone()
    conn.close()
    return row[0] if row else ""


def render_evening_routine_checklist(today_str=None):
    """Abendroutine-Checkliste, wiederverwendbar in Schlaf-Seite und Tag-abschließen-Tab."""
    today_str = today_str or date.today().isoformat()
    checks_pm = get_routine_checks(today_str, 'evening')
    for t in EVENING_ROUTINE_TASKS:
        cur = checks_pm.get(t['key'], False)
        new = st.checkbox(f"{t['icon']} {t['label']}", value=cur,
                          key=f"eve_chk_{t['key']}_{today_str}")
        if new != cur:
            set_routine_check(today_str, 'evening', t['key'], new)
            st.rerun()


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


def _parse_ki_json(raw: str) -> dict:
    """Robustly extract JSON from an LLM response that may be wrapped in markdown fences
    or contain trailing commas / other minor syntax issues."""
    import re as _re
    # Strip markdown code fences
    raw = raw.strip()
    raw = _re.sub(r'^```(?:json)?\s*', '', raw, flags=_re.IGNORECASE)
    raw = _re.sub(r'\s*```$', '', raw)
    raw = raw.strip()
    # Extract the outermost {...} block
    start = raw.find('{')
    end   = raw.rfind('}')
    if start != -1 and end != -1 and end > start:
        raw = raw[start:end + 1]
    # Remove trailing commas before } or ]
    raw = _re.sub(r',\s*([}\]])', r'\1', raw)
    return json.loads(raw)


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
  "focus_order": [123, 456],
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
        raw = resp.choices[0].message.content
        return _parse_ki_json(raw)
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
        return _parse_ki_json(resp.choices[0].message.content)
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
        return _parse_ki_json(resp.choices[0].message.content)
    except Exception as e:
        return {"error": str(e)}


def ki_daily_training_plan(api_key):
    """KI erstellt tagesoptimierten Trainingsplan basierend auf echter Session-Historie."""
    try:
        from openai import OpenAI as _OpenAI
        client = _OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)
        today = date.today()

        conn = sqlite3.connect(DB_PATH)
        sessions = conn.execute("""
            SELECT session_date, track, sets_completed, target_sets,
                   best_reps, target_reps, is_hold, clean
            FROM cal_sessions WHERE session_date >= ?
            ORDER BY session_date DESC, track
        """, ((today - timedelta(days=14)).isoformat(),)).fetchall()
        progress_rows = conn.execute(
            "SELECT track, current_level, consecutive_clean, best_reps FROM cal_progress"
        ).fetchall()
        conn.close()

        if not sessions:
            auto = get_todays_auto_plan()
            auto['source'] = 'auto'
            return auto

        session_lines = [
            f"{s[0]} | {CAL_TRACKS.get(s[1], {}).get('label', s[1])}: "
            f"{s[2]}/{s[3]} Sätze, {s[4]}/{s[5]} {'Sek' if s[6] else 'Wdh'} "
            f"{'✅' if s[7] else '⚠️'}"
            for s in sessions
        ]
        progress_lines = [
            f"{CAL_TRACKS.get(p[0], {}).get('label', p[0])}: Stufe {p[1]+1}, "
            f"{p[2]}x clean in Folge, Best: {p[3]}"
            for p in progress_rows
        ]
        track_options = ', '.join(CAL_TRACKS.keys())

        resp = client.chat.completions.create(
            model=KIMI_MODEL,
            messages=[{
                "role": "system",
                "content": (
                    f"Du bist ein erfahrener Calisthenics-Coach. Heute: {today.isoformat()} ({WOCHENTAGE[today.weekday()]}).\n"
                    f"Verfügbare Track-Keys: {track_options}\n"
                    "Regel: mindestens 48h Pause zwischen Muskelgruppen (push/pull/legs), 24h für core/skill.\n"
                    "Plane 2–4 Tracks pro Tag — kein Fullbody jeden Tag!\n"
                    "Antworte NUR mit validem JSON."
                )
            }, {
                "role": "user",
                "content": (
                    "Trainings-Historie (letzte 14 Tage):\n"
                    + "\n".join(session_lines)
                    + "\n\nAktueller Fortschritt:\n"
                    + "\n".join(progress_lines)
                    + '\n\nPlan für heute als JSON:\n'
                    '{\n'
                    '  "tracks": ["push", "core", "skill_handstand"],\n'
                    '  "rest_day": false,\n'
                    '  "rationale": "Begründung auf Deutsch warum genau diese Tracks heute",\n'
                    '  "tip": "Konkreter Tipp für heute (optional)"\n'
                    '}'
                )
            }],
            max_tokens=500,
            stream=False
        )
        result = _parse_ki_json(resp.choices[0].message.content)
        valid_tracks = [t for t in result.get('tracks', []) if t in CAL_TRACKS]

        if not valid_tracks and not result.get('rest_day'):
            auto = get_todays_auto_plan()
            auto['source'] = 'auto'
            return auto

        return {
            'tracks': valid_tracks,
            'rest_day': bool(result.get('rest_day')),
            'rationale': result.get('rationale', ''),
            'tip': result.get('tip', ''),
            'source': 'ki'
        }
    except Exception as e:
        auto = get_todays_auto_plan()
        auto['source'] = 'auto'
        return auto


def update_todays_training_entry(tracks):
    """Aktualisiert den Trainings-Eintrag für heute wenn der Plan sich ändert."""
    today_str = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    if tracks:
        names = [CAL_TRACKS.get(t, {}).get('label', t) for t in tracks]
        content = "🏋️ Calisthenics: " + ", ".join(names)
        conn.execute(
            "UPDATE entries SET content=? WHERE entry_date=? AND tags LIKE '%training%' AND done=0",
            (content, today_str)
        )
    else:
        conn.execute(
            "DELETE FROM entries WHERE entry_date=? AND tags LIKE '%training%' AND done=0",
            (today_str,)
        )
    conn.commit()
    conn.close()


# ─── KI Elite Training Coach — vollständige Übungs-Engine ──────────────

_KI_TRAINING_SYSTEM = """Du bist ein Elite-Calisthenics-Coach mit jahrzehntelangem Wissen aus Sportwissenschaft, Biomechanik und den besten Trainingsprogrammen weltweit (Gymnastics Bodies, Convict Conditioning, RedDeltaProject, FitnessFAQs, wissenschaftliche Studien zu Kraft, Progression und Recovery).

DEINE AUFGABE: Erstelle täglich den PERFEKTEN, hochpersonalisierten Trainingsplan — basierend auf echten Leistungsdaten des Nutzers. Kein Copy-Paste von Standardplänen.

══════════════════════════════════════════
KOMPLETTE EXERCISE LIBRARY
══════════════════════════════════════════

PUSH (Brust / Trizeps / Schulter):
Regression: Wall Push-up (Wand, 45°) → Elevated Push-up (Tisch) → Elevated Push-up (Stuhl) → Knee Push-up → Regular Push-up → Wide Push-up → Close (Diamond) Push-up → Decline Push-up → Archer Push-up → Pseudo Planche Push-up → Pike Push-up → Decline Pike Push-up → Wall HSPU (Fußhöhe) → Box HSPU → HSPU Negativ (5s) → Handstand Push-up → Strict Deep HSPU
Hilfsübungen: Dip Negativ, Ring Push-up, Explosive Push-up, Shoulder Tap Plank

PULL (Rücken / Bizeps):
Regression: Dead Hang (passiv, 10s) → Active Hang (Schulterblätter aktiv) → Scapular Pull-up → Inverted Row (Tischkante) → Ring Row (steil) → Ring Row (flach = horizontal) → Chin-up Negativ (5s) → Pull-up Negativ (5s) → Band-Chin-up → Band-Pull-up → Chin-up → Pull-up → Enger Pull-up → Archer Pull-up → L-Sit Pull-up → One-Arm Negativ → One-Arm Pull-up
Hilfsübungen: Face Pull (Band), Scapular Shrug, Chest-to-Bar Pull-up

LEGS (Beine / Gesäß):
Regression: Box Squat (hoch) → Box Squat (tief) → Regular Squat → Pause Squat (2s unten) → Step-up → Reverse Lunge → Forward Lunge → Split Squat → Bulgarian Split Squat → Shrimp Squat (assistiert, Stuhl) → Shrimp Squat (frei) → Pistol Squat (Box hoch) → Pistol Squat (Box tief) → Pistol Squat (assistiert) → Pistol Squat → Dragon Squat
Nordic Curl Track: Nordic Curl Negativ (5s) → Nordic Curl Negativ (8s) → Partial Nordic Curl → Nordic Curl
Hilfsübungen: Glute Bridge, Single-Leg Glute Bridge, Wall Sit, Jump Squat, Sissy Squat, Calf Raise

CORE (Rumpf):
Regression: Dead Bug (Anfänger) → Dead Bug (gestreckt) → Hollow Body Hold (gebeugt) → Hollow Body Hold (gestreckt) → Knee Plank → Plank (standard) → Plank mit Arm-Heben → Side Plank → Copenhagen Plank → Liegende Beinheber (gebeugt) → Liegende Beinheber (gestreckt) → Hängende Knieheber → Hängende L-Sit-Hold → Hängende Beinheber → Tuck L-Sit (Boden) → L-Sit (Boden) → L-Sit (Parallel Bars) → Ab Wheel (kniend) → Ab Wheel (Füße) → Dragon Flag Negativ → Dragon Flag → Front Lever Tuck → Front Lever
Hilfsübungen: V-Up, Bicycle Crunch, Toe Touch, McGill Big 3

HANDSTAND (Skill):
Wrist Mobility & Prep (täglich) → Frog Stand (5s) → Crow Pose (5-10s) → Headstand (an Wand) → Wand-Handstand Bauch zur Wand (30s) → Wand-Handstand Rücken zur Wand → Kick-up Training (10 Versuche) → Fußabnehmen von Wand (1-2s) → Freier HS (kurz) → Freier HS 5s → HS Walk → HS Push-up
Hilfsübungen: Fußabnehmen Übung, Shoulder Tap HS

MUSCLE-UP (Skill):
Explosive Pull-up (Brust zur Stange) → Dip (tief, 90°) → Dip Negativ → L-Sit Dip → Bar Muscle-up mit Band → Bar Muscle-up Negativ → Bar Muscle-up (Schwung) → Bar Muscle-up (kipping clean) → Bar Muscle-up (strict)
Hilfsübungen: High Pull, Transition Drill, Ring Muscle-up

MOBILITY & RECOVERY (für Ruhetage oder als Warm-up):
Cat-Cow, Thorax-Rotation, Hip 90/90, Deep Squat Hold, Pigeon Pose, Shoulder CARs, Band Dislocates, Wrist Circles, Foam Rolling

══════════════════════════════════════════
TRAININGS-PRINZIPIEN (immer anwenden!)
══════════════════════════════════════════

1. PROGRESSION (wenn clean geschafft):
   - 2x hintereinander alle Sätze/Reps clean → NÄCHSTE Stufe ODER +1 Rep/Set
   - Lang stagniert trotz clean → Volume-Phase (mehr Sätze) ODER Intensitätssteigerung

2. REGRESSION (wenn nicht clean):
   - < 60% der Ziel-Reps → 1 Stufe zurück in der Progression
   - < 80% der Ziel-Reps → gleiche Übung, Reps reduzieren (-2 bis -3)
   - Mehrfach nicht clean → 2 Stufen zurück + gezielte Hilfsübung
   - IMMER erklären WARUM die Regression zum Ziel führt

3. RECOVERY (Recovery-Regeln):
   - Push/Pull/Legs: mindestens 48h Pause
   - Core/Skills: 24h Pause ausreichend
   - Totale Erschöpfung in Notes erkannt: leichtere Alternativübung

4. REIHENFOLGE pro Session:
   - Skill zuerst (Technik braucht frischen Kopf)
   - Dann Kraft (Push/Pull/Legs)
   - Core zuletzt

5. SETS & REPS:
   - Anfänger: 3 Sätze (fokussierter)
   - Zielreps: nicht zu hoch (lieber 8 saubere als 15 schlechte)
   - Bei Holds: in Sekunden angeben (hold_seconds)

6. ADHS-COACHING:
   - Kurze, klare Anweisungen (1 Satz max)
   - Concrete cues die SOFORT umsetzbar sind
   - Sessions 30-45 Minuten max.

Antworte AUSSCHLIESSLICH mit validem JSON. Kein Text davor oder danach."""


def ki_generate_daily_exercises(api_key):
    """Elite-KI erstellt tagesaktuellen, vollständig personalisierten Trainingsplan."""
    try:
        from openai import OpenAI as _OpenAI
        client = _OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)
        today = date.today()

        conn = sqlite3.connect(DB_PATH)

        # Letzte 30 Tage Sessions (gesamte Performance-Historie)
        sessions = conn.execute("""
            SELECT session_date, track, exercise_name, sets_completed, target_sets,
                   best_reps, target_reps, is_hold, clean, notes
            FROM cal_sessions
            WHERE session_date >= ?
            ORDER BY session_date DESC, id
        """, ((today - timedelta(days=30)).isoformat(),)).fetchall()

        # Letzter KI-Plan (was war geplant?)
        last_plan_rows = conn.execute("""
            SELECT plan_date, track, exercise_name, sets, reps, hold_seconds
            FROM daily_training_exercises
            WHERE plan_date >= ?
            ORDER BY plan_date DESC, sort_order
        """, ((today - timedelta(days=7)).isoformat(),)).fetchall()

        conn.close()

        # Sessions formatieren
        session_lines = []
        for s in sessions:
            unit = 'Sek' if s[7] else 'Wdh'
            clean_str = 'CLEAN' if s[8] else 'NICHT CLEAN'
            note = f" (Notiz: {s[9]})" if s[9] else ""
            pct = round(s[3] / s[4] * 100) if s[4] else 0
            reps_pct = round(s[5] / s[6] * 100) if s[6] else 0
            session_lines.append(
                f"{s[0]} | {s[1]}: \"{s[2]}\" | "
                f"Sätze: {s[3]}/{s[4]} ({pct}%) | "
                f"Beste Leistung: {s[5]}/{s[6]} {unit} ({reps_pct}%) | "
                f"{clean_str}{note}"
            )

        # Geplante Pläne formatieren
        plan_lines = []
        for p in last_plan_rows:
            unit = 'Sek' if p[5] > 0 else 'Wdh'
            val = p[5] if p[5] > 0 else p[4]
            plan_lines.append(f"{p[0]} | {p[1]}: \"{p[2]}\" — Ziel: {p[3]} Sätze × {val} {unit}")

        session_text = "\n".join(session_lines) if session_lines else "Noch keine Sessions — erster Trainingstag!"
        plan_text = "\n".join(plan_lines) if plan_lines else "Noch kein vorheriger Plan vorhanden."

        # Tage-seit-letztem-Training pro Track ermitteln
        recovery_lines = []
        for track in CAL_TRACKS:
            last = max((s[0] for s in sessions if s[1] == track), default=None)
            if last:
                days = (today - date.fromisoformat(last)).days
                recovery_lines.append(f"{track}: zuletzt {last} ({days} Tag(e) Pause)")
            else:
                recovery_lines.append(f"{track}: noch nie trainiert")

        user_prompt = (
            f"Heute ist {today.isoformat()} ({WOCHENTAGE[today.weekday()]}).\n\n"
            f"RECOVERY-STATUS:\n" + "\n".join(recovery_lines) + "\n\n"
            f"TRAININGS-PERFORMANCE (letzte 30 Tage):\n{session_text}\n\n"
            f"LETZTER GEPLANTER PLAN (letzten 7 Tage):\n{plan_text}\n\n"
            "AUFGABE:\n"
            "1. Analysiere was clean war und was nicht\n"
            "2. Erkenne wer auf Recovery-Pause ist (48h Push/Pull/Legs, 24h Core/Skill)\n"
            "3. Erstelle den OPTIMALEN Plan für heute\n"
            "4. Wähle GENAU die richtige Schwierigkeit — lieber einfacher und perfekt als zu schwer und clean nicht möglich\n\n"
            "JSON-Format:\n"
            "{\n"
            '  "rest_day": false,\n'
            '  "day_rationale": "1-2 Sätze: Warum heute genau diese Übungen und Schwierigkeit",\n'
            '  "weekly_focus": "Hauptziel dieser Woche (z.B. Plank 40s stabilisieren)",\n'
            '  "tip": "1 konkreter Coaching-Tipp für heute",\n'
            '  "tracks": [\n'
            '    {\n'
            '      "track": "core",\n'
            '      "exercises": [\n'
            '        {\n'
            '          "name": "Plank",\n'
            '          "sets": 3,\n'
            '          "reps": 0,\n'
            '          "hold_seconds": 30,\n'
            '          "cue": "Bauch fest, Gesäß anspannen, Hüfte nicht durchhängen lassen",\n'
            '          "why": "Letztes Mal 25s geschafft — heute 30s als nächsten Schritt anpeilen",\n'
            '          "difficulty": 4\n'
            '        }\n'
            '      ]\n'
            '    }\n'
            '  ]\n'
            "}\n\n"
            "WICHTIG:\n"
            "- reps=0 und hold_seconds>0 wenn es eine Halteübung ist\n"
            "- Handstand NUR wenn Plank 30s+ stabil clean\n"
            "- Bei Erstsessions: IMMER mit Regression starten (Anfänger-Variante)\n"
            "- Max 4 Tracks pro Tag, 1-2 Übungen pro Track\n"
            "- difficulty 1-10 (1=sehr leicht, 10=extrem)\n"
            "- Tracks: push / pull / legs / core / skill_handstand / skill_muscleup"
        )

        resp = client.chat.completions.create(
            model=KIMI_MODEL,
            messages=[
                {"role": "system", "content": _KI_TRAINING_SYSTEM},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=2000,
            stream=False
        )
        result = _parse_ki_json(resp.choices[0].message.content)

        if result.get('rest_day'):
            return {'rest_day': True, 'tracks': [],
                    'day_rationale': result.get('day_rationale', 'KI empfiehlt Ruhetag.'),
                    'tip': result.get('tip', '')}

        tracks_data = []
        for td in result.get('tracks', []):
            track = td.get('track', '')
            exercises = []
            for ex in td.get('exercises', []):
                exercises.append({
                    'name': ex.get('name', ''),
                    'sets': max(1, int(ex.get('sets', 3))),
                    'reps': max(0, int(ex.get('reps', 0))),
                    'hold_seconds': max(0, int(ex.get('hold_seconds', 0))),
                    'cue': ex.get('cue', ''),
                    'why': ex.get('why', ''),
                    'difficulty': max(1, min(10, int(ex.get('difficulty', 5))))
                })
            if exercises:
                tracks_data.append({'track': track, 'exercises': exercises})

        if not tracks_data:
            return None

        return {
            'rest_day': False,
            'tracks': tracks_data,
            'day_rationale': result.get('day_rationale', ''),
            'weekly_focus': result.get('weekly_focus', ''),
            'tip': result.get('tip', '')
        }
    except Exception as e:
        return {'error': str(e)}


def ki_training_briefing(api_key):
    """Erstellt ein tiefes, ausführliches KI-Trainingsbriefing mit Zielen, Meilensteinen und Übungserklärungen."""
    today_str = date.today().isoformat()
    cache_key = f"training_briefing_{today_str}"
    cached = get_setting(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass

    try:
        from openai import OpenAI as _OpenAI
        client = _OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)
        today = date.today()

        conn = sqlite3.connect(DB_PATH)
        sessions = conn.execute("""
            SELECT session_date, track, exercise_name, sets_completed, target_sets,
                   best_reps, target_reps, is_hold, clean, notes
            FROM cal_sessions WHERE session_date >= ?
            ORDER BY session_date DESC, id
        """, ((today - timedelta(days=30)).isoformat(),)).fetchall()

        ki_exercises_rows = conn.execute("""
            SELECT track, exercise_name, sets, reps, hold_seconds, cue, why, difficulty
            FROM daily_training_exercises WHERE plan_date=? ORDER BY sort_order, id
        """, (today_str,)).fetchall()
        conn.close()

        prog = get_cal_progress()
        streak = get_cal_streak()

        # Heutige Übungen zusammenfassen
        ex_lines = []
        for r in ki_exercises_rows:
            track_label = CAL_TRACKS.get(r[0], {}).get('label', r[0])
            unit = f"{r[4]}s Hold" if r[4] > 0 else f"{r[3]} Wdh"
            ex_lines.append(f"- [{track_label}] {r[1]}: {r[2]} Sätze × {unit} | Schwierigkeit: {r[7]}/10 | Cue: {r[5]} | KI-Begründung: {r[6]}")

        # Progression pro Track
        prog_lines = []
        for t, p in prog.items():
            ex = get_cal_exercise(t, p['level'], p['bonus'])
            prog_lines.append(
                f"- {CAL_TRACKS[t]['label']}: Level {p['level']+1}/{len(CAL_TRACKS[t]['levels'])} "
                f"→ aktuelle Übung: {ex['name']}"
            )

        # Recovery Status
        recovery_lines = []
        for track in CAL_TRACKS:
            last = max((s[0] for s in sessions if s[1] == track), default=None)
            days = (today - date.fromisoformat(last)).days if last else None
            recovery_lines.append(f"- {CAL_TRACKS[track]['label']}: {'noch nie trainiert' if not last else f'zuletzt {last} ({days}d Pause)'}")

        # Letzte 10 Sessions
        sess_lines = []
        for s in sessions[:15]:
            unit = 'Sek' if s[7] else 'Wdh'
            sess_lines.append(
                f"- {s[0]} [{CAL_TRACKS.get(s[1],{}).get('label',s[1])}] {s[2]}: "
                f"{s[3]}/{s[4]} Sätze, {s[5]}/{s[6]} {unit} {'✅' if s[8] else '❌'}"
                + (f" | Notiz: {s[9]}" if s[9] else "")
            )

        ex_block = "\n".join(ex_lines) if ex_lines else "Noch kein KI-Plan für heute — erstelle zuerst einen KI-Plan."
        prog_block = "\n".join(prog_lines)
        rec_block = "\n".join(recovery_lines)
        sess_block = "\n".join(sess_lines) if sess_lines else "Noch keine Sessions."

        system_prompt = (
            "Du bist Angelo's persönlicher Elite-Calisthenics-Coach. "
            "Du kennst seine gesamte Trainingsgeschichte und redest direkt, ehrlich und motivierend mit ihm. "
            "Kein generisches Fitnessbuch-Blabla — alles konkret auf seine echten Daten bezogen. "
            "Antworte AUSSCHLIESSLICH mit validem JSON."
        )

        user_prompt = f"""Heute: {today_str} | Streak: {streak['current']} Tage | Gesamt: {streak['total_sessions']} Einheiten

PROGRESSION PRO TRACK:
{prog_block}

RECOVERY STATUS:
{rec_block}

HEUTIGE ÜBUNGEN (KI-Plan):
{ex_block}

LETZTE 15 SESSIONS:
{sess_block}

Erstelle jetzt ein detailliertes, ausführliches Trainingsbriefing. JSON-Format:
{{
  "ueberziel": "Das übergeordnete langfristige Calisthenics-Ziel basierend auf seinem aktuellen Level (2-3 Sätze, konkret und persönlich)",
  "meilensteine": [
    {{
      "name": "Meilenstein-Name (kurz)",
      "status": "erreicht|in_arbeit|offen",
      "beschreibung": "Was dieser Meilenstein bedeutet und warum er wichtig ist",
      "stand": "Aktueller Stand bezogen auf seine echten Daten"
    }}
  ],
  "ziel_heute": "Das konkrete Ziel für heute in 1 Satz",
  "warum_heute": "Warum genau dieses Ziel heute? Recovery, Progression-Timing, Datenbegründung — 3-4 Sätze",
  "verbindung_zum_ziel": "Wie führen die heutigen Übungen direkt zum übergeordneten Ziel? Konkrete mechanische und physiologische Erklärung — 3-4 Sätze",
  "uebungen": [
    {{
      "name": "Übungsname exakt wie im Plan",
      "track": "Track-Label",
      "was_trainiert": "Welche Muskeln/Bewegungsmuster/Fähigkeiten werden trainiert (detailliert)",
      "warum_jetzt": "Warum genau diese Übung auf diesem Level jetzt — bezogen auf seine Progressionsdaten",
      "biomechanik": "Kurze biomechanische Erklärung: was passiert im Körper während dieser Übung",
      "langzeitwirkung": "Wie baut diese Übung die Grundlage für den nächsten Progressionsschritt und das Gesamtziel",
      "mental_cue": "1 mentaler Fokus-Satz für die Ausführung"
    }}
  ],
  "coach_wort": "1 persönliches, ehrliches Coach-Wort für heute — kein Motivations-Bullshit, sondern was Angelo wirklich hören muss"
}}

WICHTIG: Mindestens 3 Meilensteine. Für jede heutige Übung ein Eintrag in 'uebungen'. Sei ausführlich und konkret, keine Allgemeinplätze."""

        resp = client.chat.completions.create(
            model=KIMI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=3000,
            stream=False
        )
        result = _parse_ki_json(resp.choices[0].message.content)
        if result and not result.get('error'):
            set_setting(cache_key, json.dumps(result, ensure_ascii=False))
        return result
    except Exception as e:
        return {'error': str(e)}


# ══════════════════════════════════════════════════════════════════════
# KI ZENTRAL-GEHIRN — Tages-Briefing, Coach-Leiste, proaktive Anpassung
# ══════════════════════════════════════════════════════════════════════

_KI_BRIEFING_SYSTEM = """Du bist Angelo's persönlicher ADHS-Coach. Du kennst ihn, du kennst seine Daten, und du redest direkt mit ihm — kein Therapeuten-Speak, kein Datendump.

DEINE AUFGABE: Analysiere alle vorliegenden Daten und erstelle ein ehrliches, personalisiertes Tages-Briefing. Du triffst Entscheidungen FÜR ihn — weniger Entscheidungen = weniger ADHS-Overhead.

ENERGIE-BERECHNUNG (energy_level 1–5, Daten als quality_pct 0-100):
- quality_pct ≤ 40 (schlechter Schlaf) → max 2
- quality_pct 41-60 (mittelmäßig) → 3
- quality_pct 61-80 (gut) → 4
- quality_pct > 80 (sehr gut) → 5
- Kein Schlafeintrag für heute → 3 (Annahme)
- Mehrere schlechte Nächte hintereinander → −1 kumulativ

FOCUS_MODE:
- energy 1–2 → "recovery" (nur leichte Tasks, kein komplexes Denken, kürzere Sessions)
- energy 3 → "light" (mittlere Aufgaben, kurze Sessions à 25 min)
- energy 4 → "normal" (normaler produktiver Tag)
- energy 5 → "deep" (perfekt für komplexe oder kreative Aufgaben, 50-min-Blöcke)

TASK-PRIORISIERUNG:
- Energie niedrig → einfachere Tasks ZUERST, komplexe Tasks hinten oder auf morgen
- Energie hoch → wichtigste und schwerste Task ZUERST (eat the frog)
- Berücksichtige Tags und Deadlines aus den Task-Daten

DAY_MESSAGE Regeln:
- Maximal 2 kurze Sätze
- Du-Form, direkt, wie ein guter Kumpel der Trainer ist
- Ehrlich: wenn Schlaf schlecht war → das ANSPRECHEN, nicht ignorieren
- Kein Motivations-Bla-Bla ("Du schaffst das!")
- Konkret was heute passiert: "Heute light — 2 Tasks, dann Schluss."

ADAPTATIONS (max 3, nur wenn wirklich abweichend von Standard):
- Konkrete, umsetzbare Anpassungen
- Beispiel: "Training heute leichter ansetzen — zu wenig Schlaf für volle Intensität"
- Beispiel: "Fokus-Session auf 25 min kürzen, dann kurze Pause"
- Beispiel: "Task 'X' auf morgen — heute reicht die Energie nicht"
- LEER lassen wenn normaler Tag ohne besondere Anpassungen

Antworte NUR mit validem JSON, kein Text davor oder danach:
{
  "energy_level": 3,
  "focus_mode": "normal",
  "day_message": "Direkte 2-Satz-Nachricht an Angelo",
  "top_priority": "Konkret welche Aufgabe ZUERST — leer wenn keine Tasks vorhanden",
  "adaptations": ["Anpassung 1", "Anpassung 2"],
  "task_order": [id1, id2, id3],
  "training_note": "1 Satz zur heutigen Training-Empfehlung basierend auf Energie — leer wenn kein Training"
}"""


def save_ki_briefing(data):
    set_setting(f"ki_briefing_{date.today().isoformat()}", json.dumps(data, ensure_ascii=False))


def get_ki_briefing():
    raw = get_setting(f"ki_briefing_{date.today().isoformat()}")
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    return None


def ki_morning_briefing(api_key):
    """Zentrale Tages-Analyse: alle Daten → persönlicher Coach-Plan für den ganzen Tag."""
    try:
        from openai import OpenAI as _OpenAI
        client = _OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)
        today = date.today()
        today_str = today.isoformat()

        conn = sqlite3.connect(DB_PATH)

        # Schlaf heute & letzte 7 Tage (quality_pct=0-100, wake_time)
        sleep_today = conn.execute(
            "SELECT quality_pct, bedtime, wake_time FROM sleep_logs WHERE log_date=? LIMIT 1",
            (today_str,)
        ).fetchone()
        sleep_hist = conn.execute(
            "SELECT log_date, quality_pct, bedtime, wake_time FROM sleep_logs WHERE log_date>=? ORDER BY log_date DESC",
            ((today - timedelta(days=7)).isoformat(),)
        ).fetchall()

        # Tasks heute
        brain_tasks = conn.execute(
            """SELECT id, content, priority, estimate_minutes, tags, deadline
               FROM entries WHERE entry_date=? AND entry_type='brain' AND done=0
               ORDER BY priority DESC""",
            (today_str,)
        ).fetchall()

        # Habit Streaks
        habits = conn.execute("SELECT id, name, icon FROM habits LIMIT 10").fetchall()
        habit_streaks = []
        for h in habits:
            streak = conn.execute(
                "SELECT COUNT(*) FROM habit_logs WHERE habit_id=? AND log_date>=?",
                (h[0], (today - timedelta(days=7)).isoformat())
            ).fetchone()[0]
            habit_streaks.append((h[1], h[2], streak))

        # Training heute
        ki_exercises = conn.execute(
            "SELECT track, exercise_name, sets, reps, hold_seconds FROM daily_training_exercises WHERE plan_date=?",
            (today_str,)
        ).fetchall()
        training_plan_raw = get_setting(f"training_plan_{today_str}")
        training_plan = json.loads(training_plan_raw) if training_plan_raw else None

        # Letzte Trainingssession (gestern)
        yesterday_str = (today - timedelta(days=1)).isoformat()
        yesterday_sessions = conn.execute(
            "SELECT track, exercise_name, clean FROM cal_sessions WHERE session_date=?",
            (yesterday_str,)
        ).fetchall()

        conn.close()

        # ── Context aufbauen ──
        if sleep_today:
            q_pct, bt, wt = sleep_today
            q_stars = round((q_pct or 0) / 20)  # 0-100 → 0-5
            sleep_text = f"Heute Nacht: Qualität {q_stars}/5 ({q_pct}%) | eingeschlafen {bt or '?'}, aufgestanden {wt or '?'}"
        else:
            sleep_text = "Kein Schlafeintrag für heute — Annahme: ausreichend"

        if sleep_hist:
            hist_lines = [
                f"  {s[0]}: Qualität {round((s[1] or 0)/20)}/5 | {s[2] or '?'} → {s[3] or '?'}"
                for s in sleep_hist
            ]
            sleep_text += "\nLetzte 7 Nächte:\n" + "\n".join(hist_lines)

        if brain_tasks:
            task_lines = []
            for t in brain_tasks:
                dead = f", Deadline: {t[5]}" if t[5] else ""
                task_lines.append(f"  ID={t[0]}: \"{t[1]}\" | ~{t[3] or '?'}min | Tags: {t[4] or 'keine'}{dead}")
            tasks_text = "Tasks für heute:\n" + "\n".join(task_lines)
        else:
            tasks_text = "Noch keine Tasks für heute eingetragen"

        if ki_exercises:
            ex_lines = [f"  {r[0]}: {r[1]} — {r[2]}× {'Sek' if r[4] else 'Wdh'}" for r in ki_exercises]
            training_text = "KI-Trainingsplan für heute:\n" + "\n".join(ex_lines)
        elif training_plan and training_plan.get('rest_day'):
            training_text = "Heute ist Ruhetag (geplant)"
        elif training_plan and training_plan.get('tracks'):
            training_text = "Training geplant: " + ", ".join(training_plan['tracks'])
        else:
            training_text = "Noch kein Trainingsplan für heute"

        if habit_streaks:
            habits_text = "Habits (letzte 7 Tage):\n" + "\n".join(
                f"  {h[1]} {h[0]}: {h[2]}/7 Tage" for h in habit_streaks
            )
        else:
            habits_text = "Keine Habits konfiguriert"

        user_prompt = (
            f"Datum: {today_str} ({WOCHENTAGE[today.weekday()]})\n\n"
            f"SCHLAF:\n{sleep_text}\n\n"
            f"AUFGABEN:\n{tasks_text}\n\n"
            f"TRAINING:\n{training_text}\n\n"
            f"HABITS:\n{habits_text}\n\n"
            "Erstelle jetzt Angelo's Tages-Briefing."
        )

        resp = client.chat.completions.create(
            model=KIMI_MODEL,
            messages=[
                {"role": "system", "content": _KI_BRIEFING_SYSTEM},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=800,
            stream=False
        )
        result = _parse_ki_json(resp.choices[0].message.content)
        result.setdefault('energy_level', 3)
        result.setdefault('focus_mode', 'normal')
        result.setdefault('day_message', '')
        result.setdefault('top_priority', '')
        result.setdefault('adaptations', [])
        result.setdefault('task_order', [])
        result.setdefault('training_note', '')
        save_ki_briefing(result)
        return result
    except Exception as e:
        fallback = {
            'energy_level': 3, 'focus_mode': 'normal',
            'day_message': 'Starte ruhig. Ein Schritt nach dem anderen.',
            'top_priority': '', 'adaptations': [], 'task_order': [], 'training_note': '',
            '_error': str(e)
        }
        save_ki_briefing(fallback)
        return fallback


def _render_ki_coach_bar():
    """Permanente KI-Coach-Leiste — erscheint auf JEDER Seite automatisch."""
    api_key = get_setting('nvidia_api_key', '')

    if not api_key:
        st.markdown("""<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);
            border-radius:10px;padding:9px 16px;margin-bottom:16px;
            display:flex;align-items:center;gap:8px">
            <span style="font-size:13px">🤖</span>
            <span style="font-size:11px;color:rgba(255,255,255,0.3)">
              KI-Coach inaktiv — NVIDIA API-Key in <strong style="color:rgba(255,255,255,0.5)">Einstellungen</strong> hinterlegen
            </span>
        </div>""", unsafe_allow_html=True)
        return

    briefing = get_ki_briefing()
    if briefing is None:
        with st.spinner("KI analysiert deinen Tag …"):
            briefing = ki_morning_briefing(api_key)

    if not briefing:
        return

    energy = max(1, min(5, int(briefing.get('energy_level', 3))))
    focus_mode = briefing.get('focus_mode', 'normal')
    day_message = briefing.get('day_message', '')
    top_priority = briefing.get('top_priority', '')
    adaptations = briefing.get('adaptations', [])
    training_note = briefing.get('training_note', '')

    _E_COLORS = ['#e74c3c', '#e67e22', '#f1c40f', '#2ecc71', '#00d4ff']
    _E_LABELS  = ['Erschöpft', 'Niedrig', 'Okay', 'Gut', 'Top-Form']
    _E_EMOJI   = ['😴', '😑', '🙂', '💪', '🔥']
    e_color = _E_COLORS[energy - 1]
    e_label = _E_LABELS[energy - 1]
    e_emoji = _E_EMOJI[energy - 1]

    _FOCUS_MAP = {
        'deep':     ('🧠 Deep Work',   '#00d4ff'),
        'light':    ('⚡ Light Mode',   '#f39c12'),
        'recovery': ('🌿 Recovery',     '#a29bfe'),
        'normal':   ('✅ Normal',       '#2ecc71'),
    }
    focus_label, focus_color = _FOCUS_MAP.get(focus_mode, ('✅ Normal', '#2ecc71'))

    bar_key = f"ki_bar_expanded_{date.today().isoformat()}"
    is_expanded = st.session_state.get(bar_key, True)

    if is_expanded:
        adapt_html = ""
        if adaptations:
            items = "".join(
                f'<li style="margin:2px 0;color:rgba(255,255,255,0.55);font-size:11px">{a}</li>'
                for a in adaptations[:3]
            )
            adapt_html = f'<ul style="margin:8px 0 0 14px;padding:0;list-style:disc">{items}</ul>'

        priority_html = (
            f'<div style="font-size:12px;color:#ffd700;margin-top:8px">'
            f'🎯 Starte mit: <strong>{top_priority}</strong></div>'
            if top_priority else ''
        )
        training_html = (
            f'<div style="font-size:11px;color:rgba(162,155,254,0.85);margin-top:6px">'
            f'🏋️ {training_note}</div>'
            if training_note else ''
        )

        energy_bar = "".join(
            f'<div style="width:14px;height:14px;border-radius:3px;'
            f'background:{"' + e_color + '" if i < energy else "rgba(255,255,255,0.08)"};'
            f'margin-right:3px"></div>'
            for i in range(5)
        )

        st.markdown(f"""<div style="background:linear-gradient(135deg,rgba(0,212,255,0.06),rgba(162,155,254,0.05));
            border:1px solid rgba(0,212,255,0.18);border-radius:14px;padding:14px 18px;margin-bottom:14px">
          <div style="display:flex;align-items:flex-start;gap:14px;flex-wrap:wrap">
            <div style="min-width:110px">
              <div style="font-size:9px;color:rgba(255,255,255,0.3);letter-spacing:1.5px;
                          text-transform:uppercase;margin-bottom:4px">ENERGIE HEUTE</div>
              <div style="display:flex;align-items:center;margin-bottom:4px">{energy_bar}</div>
              <div style="font-size:12px;font-weight:700;color:{e_color}">{e_emoji} {e_label}</div>
            </div>
            <div style="border-left:1px solid rgba(255,255,255,0.08);padding-left:14px;flex:1;min-width:180px">
              <div style="margin-bottom:6px">
                <span style="font-size:10px;color:{focus_color};background:{focus_color}18;
                  border:1px solid {focus_color}33;padding:2px 9px;border-radius:6px;font-weight:700">{focus_label}</span>
              </div>
              <div style="font-size:13px;color:rgba(255,255,255,0.85);font-style:italic;line-height:1.5">"{day_message}"</div>
              {priority_html}
              {training_html}
              {adapt_html}
            </div>
          </div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div style="background:rgba(0,212,255,0.03);border:1px solid rgba(0,212,255,0.1);
            border-radius:10px;padding:8px 16px;margin-bottom:12px;
            display:flex;align-items:center;gap:10px">
          <span style="font-size:15px">{e_emoji}</span>
          <span style="font-size:11px;color:rgba(255,255,255,0.45);font-style:italic;flex:1">{day_message}</span>
          <span style="font-size:10px;color:{focus_color};font-weight:700">{focus_label}</span>
        </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        lbl = "▲ Einklappen" if is_expanded else "▼ KI-Coach anzeigen"
        if st.button(lbl, key="ki_bar_toggle_btn", use_container_width=True):
            st.session_state[bar_key] = not is_expanded
            st.rerun()
    with c2:
        if st.button("🔄 Neu analysieren", key="ki_bar_refresh_btn", use_container_width=True):
            conn_d = sqlite3.connect(DB_PATH)
            conn_d.execute("DELETE FROM settings WHERE key=?",
                           (f"ki_briefing_{date.today().isoformat()}",))
            conn_d.commit()
            conn_d.close()
            st.rerun()


def ki_get_task_priorities():
    """Gibt die KI-priorisierten Task-IDs aus dem Tages-Briefing zurück."""
    briefing = get_ki_briefing()
    if not briefing:
        return []
    return [int(x) for x in briefing.get('task_order', []) if str(x).isdigit()]


def ki_get_focus_mode():
    """Gibt den aktuellen Focus Mode aus dem Briefing zurück."""
    briefing = get_ki_briefing()
    return briefing.get('focus_mode', 'normal') if briefing else 'normal'


def ki_get_energy_level():
    """Gibt den Energie-Level (1-5) aus dem Briefing zurück."""
    briefing = get_ki_briefing()
    return max(1, min(5, int(briefing.get('energy_level', 3)))) if briefing else 3


def ki_get_training_note():
    """Gibt den KI-Trainingshinweis aus dem Briefing zurück."""
    briefing = get_ki_briefing()
    return briefing.get('training_note', '') if briefing else ''


def ki_get_top_priority():
    """Gibt die KI-Priorität-1-Aufgabe zurück."""
    briefing = get_ki_briefing()
    return briefing.get('top_priority', '') if briefing else ''


def ki_get_adaptations():
    """Gibt die KI-Tagesanpassungen zurück."""
    briefing = get_ki_briefing()
    return briefing.get('adaptations', []) if briefing else []


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
        return _parse_ki_json(resp.choices[0].message.content)
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
        return _parse_ki_json(resp.choices[0].message.content)
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
    brain_rows      = [r for r in rows if r[1] == "brain" and not r[9]]
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

    # ── KI Task-Priorisierung (nach Brain Dump, vor Highlight-Auswahl) ──
    if has_brain and brain_rows:
        ki_order = ki_get_task_priorities()
        energy = ki_get_energy_level()
        focus = ki_get_focus_mode()
        top_prio = ki_get_top_priority()
        adaptations = ki_get_adaptations()

        focus_desc = {
            'deep': 'Starte mit der schwersten Aufgabe — volle Energie vorhanden.',
            'light': 'Leichtere Aufgaben bevorzugen — mittlere Energie.',
            'recovery': 'Nur einfache Tasks — heute Energie schonen.',
            'normal': 'Normaler Tag — wichtigste Task zuerst.'
        }.get(focus, '')

        _e_colors = ['#e74c3c', '#e67e22', '#f1c40f', '#2ecc71', '#00d4ff']
        _e_emoji   = ['😴', '😑', '🙂', '💪', '🔥']
        e_col  = _e_colors[energy - 1]
        e_em   = _e_emoji[energy - 1]

        # Tasks in KI-Reihenfolge sortieren (unbekannte IDs ans Ende)
        id_to_row = {r[0]: r for r in brain_rows}
        ki_sorted = [id_to_row[i] for i in ki_order if i in id_to_row]
        remaining = [r for r in brain_rows if r[0] not in set(ki_order)]
        ordered_tasks = ki_sorted + remaining

        adapt_html = ""
        if adaptations:
            items = "".join(f'<li style="font-size:11px;color:rgba(255,255,255,0.55);margin:3px 0">{a}</li>' for a in adaptations[:3])
            adapt_html = f'<ul style="margin:6px 0 0 16px;padding:0;list-style:disc">{items}</ul>'

        task_items_html = ""
        for idx, r in enumerate(ordered_tasks):
            tid, content = r[0], r[2]
            rank_color = '#ffd700' if idx == 0 else ('rgba(255,255,255,0.6)' if idx == 1 else 'rgba(255,255,255,0.35)')
            rank_label = '① JETZT' if idx == 0 else (f'② danach' if idx == 1 else f'③+')
            task_items_html += (
                f'<div style="display:flex;align-items:flex-start;gap:10px;padding:8px 0;'
                f'border-bottom:1px solid rgba(255,255,255,0.05)">'
                f'<span style="font-size:10px;font-weight:800;color:{rank_color};min-width:52px;'
                f'padding-top:2px">{rank_label}</span>'
                f'<span style="font-size:12.5px;color:rgba(255,255,255,0.8)">{content}</span>'
                f'</div>'
            )

        st.markdown(f"""<div style="background:linear-gradient(135deg,rgba(0,212,255,0.05),rgba(255,215,0,0.04));
            border:1px solid rgba(0,212,255,0.2);border-radius:14px;padding:16px 20px;margin:12px 0">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap">
            <span style="font-size:16px">🤖</span>
            <span style="font-size:13px;font-weight:800;color:white">KI-Priorisierung für heute</span>
            <span style="font-size:10px;font-weight:700;color:{e_col};background:{e_col}18;
              border:1px solid {e_col}33;padding:2px 8px;border-radius:6px">{e_em} Energie {energy}/5</span>
          </div>
          <div style="font-size:11.5px;color:rgba(0,212,255,0.7);margin-bottom:10px;font-style:italic">{focus_desc}</div>
          {task_items_html}
          {adapt_html}
        </div>""", unsafe_allow_html=True)

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
                    if st.form_submit_button("Speichern", use_container_width=True):
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

                if st.button("🗑️ Löschen", key=f"pl_del_{eid}", use_container_width=True):
                    delete_entry(eid)
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
    phase       = st.session_state.get('focus_phase', 'confirm')
    task_id     = st.session_state.get('focus_task_id')
    task_name   = st.session_state.get('focus_task_name', '?')
    task_estimate = st.session_state.get('focus_task_estimate', 25)

    st.markdown("""<style>
    @keyframes pulseGlow {
        0%,100% { box-shadow: 0 0 0 0 rgba(0,212,255,0.0); }
        50%      { box-shadow: 0 0 14px 4px rgba(0,212,255,0.35); }
    }
    @keyframes completePop {
        0%   { transform: scale(1); }
        40%  { transform: scale(1.04); }
        100% { transform: scale(1); }
    }
    @keyframes missionComplete {
        0%   { opacity:0; transform: translateY(10px) scale(0.95); }
        100% { opacity:1; transform: translateY(0) scale(1); }
    }
    @keyframes xpFloat {
        0%   { opacity:1; transform:translateY(0) scale(1.1); }
        100% { opacity:0; transform:translateY(-28px) scale(0.8); }
    }
    .focus-hdr {
        text-align:center; font-size:11px; letter-spacing:3px; text-transform:uppercase;
        color:#00d4ff; opacity:.7; padding:10px 0 4px;
    }
    .focus-task {
        text-align:center; font-size:22px; font-weight:700; padding:6px 0 14px;
    }
    .pomo-time {
        text-align:center; font-size:80px; font-weight:900; color:#00d4ff;
        letter-spacing:6px; line-height:1; padding:12px 0;
        text-shadow: 0 0 40px rgba(0,212,255,0.4);
    }
    .pomo-time.urgent { color:#ff6b6b; text-shadow: 0 0 40px rgba(255,107,107,0.5); }
    .quest-panel {
        background: rgba(0,0,0,0.25);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 14px;
        padding: 14px 18px;
        margin-top: 18px;
    }
    .quest-header {
        display:flex; align-items:center; justify-content:space-between;
        margin-bottom: 10px;
    }
    .quest-label {
        font-size:10px; color:rgba(255,255,255,0.35); letter-spacing:2px;
        text-transform:uppercase; font-weight:700;
    }
    .quest-count {
        font-size:12px; font-weight:700;
    }
    .quest-step {
        display:flex; align-items:center; gap:10px;
        border-radius:10px; padding:9px 12px; margin:5px 0;
        border:1px solid rgba(255,255,255,0.06);
        background:rgba(255,255,255,0.025);
        transition: all 0.3s ease;
    }
    .quest-step.active {
        border-color:rgba(0,212,255,0.35);
        background:rgba(0,212,255,0.06);
        animation: pulseGlow 2.5s infinite;
    }
    .quest-step.done {
        border-color:rgba(46,204,113,0.3);
        background:rgba(46,204,113,0.06);
        animation: completePop 0.35s ease;
    }
    .quest-step.locked {
        opacity:0.4;
    }
    .quest-num {
        width:22px; height:22px; border-radius:50%;
        display:flex; align-items:center; justify-content:center;
        font-size:11px; font-weight:700; flex-shrink:0;
        background:rgba(255,255,255,0.07); color:rgba(255,255,255,0.5);
    }
    .quest-num.active { background:rgba(0,212,255,0.2); color:#00d4ff; }
    .quest-num.done   { background:rgba(46,204,113,0.25); color:#2ecc71; }
    .quest-text {
        flex:1; font-size:13px; font-weight:500; color:white;
    }
    .quest-text.done {
        text-decoration:line-through; color:rgba(255,255,255,0.35);
    }
    .quest-xp {
        font-size:10px; font-weight:700; color:#ffd700;
        background:rgba(255,215,0,0.1); padding:2px 7px;
        border-radius:5px; flex-shrink:0;
    }
    .quest-xp.done { color:#2ecc71; background:rgba(46,204,113,0.1); }
    .mission-complete {
        text-align:center; padding:14px;
        background:linear-gradient(135deg,rgba(46,204,113,0.15),rgba(0,212,255,0.08));
        border:1px solid rgba(46,204,113,0.35); border-radius:12px;
        animation: missionComplete 0.5s ease;
        margin-top:12px;
    }
    .round-badge {
        display:inline-flex; align-items:center; gap:6px;
        background:rgba(162,155,254,0.12); border:1px solid rgba(162,155,254,0.25);
        border-radius:20px; padding:4px 14px; font-size:12px; font-weight:700;
        color:#a29bfe; margin-bottom:12px;
    }
    /* Hide step checkbox labels */
    div[data-testid="stCheckbox"] > label > div[data-testid="stMarkdownContainer"] > p {
        display:none !important;
    }
    </style>""", unsafe_allow_html=True)

    _, center, _ = st.columns([0.5, 3, 0.5])

    # ── Phase 1: Anti-Distraktion + Schritt-Vorschau ───────────────
    if phase == 'confirm':
        with center:
            st.markdown('<div class="focus-hdr">🎯 Fokus Modus</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="focus-task">{task_name}</div>', unsafe_allow_html=True)

            # Zeige Task-Schritte als Vorschau
            preview_steps = get_task_steps(task_id) if task_id else []
            if preview_steps:
                steps_html = ""
                for s in preview_steps:
                    steps_html += (
                        f'<div style="display:flex;align-items:center;gap:10px;padding:7px 12px;'
                        f'background:rgba(255,255,255,0.025);border-radius:8px;margin:4px 0;'
                        f'border:1px solid rgba(255,255,255,0.05)">'
                        f'<span style="font-size:10px;color:rgba(255,255,255,0.3);min-width:18px">{s["step_number"]}.</span>'
                        f'<span style="font-size:12px;color:rgba(255,255,255,0.7)">{s["content"]}</span>'
                        f'</div>'
                    )
                st.markdown(
                    f'<div style="margin-bottom:14px">'
                    f'<div style="font-size:10px;color:rgba(255,255,255,0.35);letter-spacing:1.5px;'
                    f'text-transform:uppercase;margin-bottom:6px">🗡️ {len(preview_steps)} Mission-Ziele</div>'
                    f'{steps_html}</div>',
                    unsafe_allow_html=True
                )

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
                    st.session_state.focus_steps = get_task_steps(task_id) if task_id else []
                    st.session_state.focus_block_start = datetime.utcnow().isoformat()
                    st.rerun()
            else:
                st.button("✅ Alle Häkchen setzen zum Starten", disabled=True, use_container_width=True)
            st.write("")
            if st.button("← Abbrechen", use_container_width=True, key="fc_cancel_confirm"):
                _clear_focus_mode()
                st.rerun()

    # ── Phase 2: Pomodoro Countdown + Gamified Steps ───────────────
    elif phase == 'pomodoro':
        round_num = st.session_state.get('focus_round', 1)
        start_str = st.session_state.get('focus_pomodoro_start', datetime.utcnow().isoformat())
        block_start = st.session_state.get('focus_block_start', start_str)
        try:
            elapsed = int((datetime.utcnow() - datetime.fromisoformat(start_str)).total_seconds())
        except Exception:
            elapsed = 0
        remaining = max(0, POMODORO_DURATION - elapsed)
        mins, secs = remaining // 60, remaining % 60
        pct = min(1.0, elapsed / POMODORO_DURATION)

        with center:
            # Round-Badge
            st.markdown(
                f'<div style="text-align:center"><span class="round-badge">'
                f'🎯 FOKUS · RUNDE {round_num}</span></div>',
                unsafe_allow_html=True
            )
            st.markdown(f'<div class="focus-task">{task_name}</div>', unsafe_allow_html=True)

            # Timer
            time_color = "urgent" if remaining < 120 else ""
            st.markdown(f'<div class="pomo-time {time_color}">{mins:02d}:{secs:02d}</div>', unsafe_allow_html=True)

            # Progress bar mit Segment-Markierungen
            bar_pct = int(pct * 100)
            seg_html = ""
            for seg in [25, 50, 75]:
                seg_html += (
                    f'<div style="position:absolute;left:{seg}%;top:-2px;width:2px;height:8px;'
                    f'background:rgba(0,0,0,0.4);z-index:2"></div>'
                )
            st.markdown(
                f'<div style="position:relative;height:6px;background:rgba(255,255,255,0.06);'
                f'border-radius:3px;margin:8px 0 4px">{seg_html}'
                f'<div style="position:absolute;top:0;left:0;height:100%;width:{bar_pct}%;'
                f'background:{"#ff6b6b" if remaining < 120 else "#00d4ff"};border-radius:3px;'
                f'transition:width 0.8s ease"></div></div>',
                unsafe_allow_html=True
            )
            st.caption(f"{bar_pct}% · {round(elapsed/60, 1)} Min absolviert")

            if remaining == 0:
                st.markdown(
                    '<div style="text-align:center;padding:10px;background:rgba(255,215,0,0.1);'
                    'border-radius:10px;border:1px solid rgba(255,215,0,0.3);font-weight:700;color:#ffd700">'
                    '⏰ 25 Minuten voll! Wie weiter?</div>',
                    unsafe_allow_html=True
                )

            st.write("")
            btn1, btn2, btn3, btn4 = st.columns(4)
            with btn1:
                if st.button("✅ Aufgabe fertig", use_container_width=True, type="primary"):
                    done_secs = st.session_state.get('focus_total_seconds', 0) + (POMODORO_DURATION - remaining)
                    steps_now = st.session_state.get('focus_steps', [])
                    s_done = sum(1 for s in steps_now if s.get('done'))
                    log_focus_block(task_id, task_name, block_start,
                                    datetime.utcnow().isoformat(), POMODORO_DURATION - remaining,
                                    round_num, s_done, len(steps_now))
                    toggle_done(task_id, True, elapsed_seconds=done_secs,
                                points=compute_points(done_secs, task_estimate))
                    st.session_state.focus_phase = 'review'
                    st.session_state.focus_total_seconds = done_secs
                    st.rerun()
            with btn2:
                if st.button("🔄 Noch eine Runde", use_container_width=True):
                    steps_now = st.session_state.get('focus_steps', [])
                    s_done = sum(1 for s in steps_now if s.get('done'))
                    log_focus_block(task_id, task_name, block_start,
                                    datetime.utcnow().isoformat(), POMODORO_DURATION - remaining,
                                    round_num, s_done, len(steps_now))
                    prev = st.session_state.get('focus_total_seconds', 0)
                    st.session_state.focus_total_seconds = prev + (POMODORO_DURATION - remaining)
                    st.session_state.focus_round = round_num + 1
                    st.session_state.focus_pomodoro_start = datetime.utcnow().isoformat()
                    st.session_state.focus_block_start = datetime.utcnow().isoformat()
                    st.rerun()
            with btn3:
                if st.button("🧺 Haushalts-Pause", use_container_width=True):
                    steps_now = st.session_state.get('focus_steps', [])
                    s_done = sum(1 for s in steps_now if s.get('done'))
                    log_focus_block(task_id, task_name, block_start,
                                    datetime.utcnow().isoformat(), POMODORO_DURATION - remaining,
                                    round_num, s_done, len(steps_now))
                    prev = st.session_state.get('focus_total_seconds', 0)
                    st.session_state.focus_total_seconds = prev + (POMODORO_DURATION - remaining)
                    st.session_state.focus_phase = 'household_break'
                    st.rerun()
            with btn4:
                if st.button("🚫 Abbrechen", use_container_width=True):
                    _clear_focus_mode()
                    st.rerun()

            # ── GAMIFIED QUEST STEPS ────────────────────────────────
            steps = st.session_state.get('focus_steps', [])
            if steps:
                done_n    = sum(1 for s in steps if s.get('done'))
                total_n   = len(steps)
                all_done  = done_n == total_n
                pct_steps = done_n / total_n if total_n else 0

                # Progress-Header
                count_color = "#2ecc71" if all_done else "#00d4ff"
                count_text  = "🔥 ALLE ZIELE ERREICHT!" if all_done else f"{done_n}/{total_n} erledigt"

                quest_bar_w = int(pct_steps * 100)
                st.markdown(
                    f'<div class="quest-panel">'
                    f'<div class="quest-header">'
                    f'<span class="quest-label">🗡️ Mission-Ziele</span>'
                    f'<span class="quest-count" style="color:{count_color}">{count_text}</span>'
                    f'</div>'
                    f'<div style="height:5px;background:rgba(255,255,255,0.05);border-radius:3px;margin-bottom:12px">'
                    f'<div style="width:{quest_bar_w}%;height:100%;border-radius:3px;'
                    f'background:{"linear-gradient(90deg,#2ecc71,#00ff88)" if all_done else "linear-gradient(90deg,#00d4ff,#0099cc)"};'
                    f'transition:width 0.6s ease"></div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

                # Nächster offener Step (aktiv)
                next_step_id = next((s['id'] for s in steps if not s.get('done')), None)

                for step in steps:
                    is_done   = step.get('done', False)
                    is_active = (not is_done) and (step['id'] == next_step_id)
                    is_locked = (not is_done) and (step['id'] != next_step_id)

                    css_cls     = "done" if is_done else ("active" if is_active else "locked")
                    num_cls     = css_cls
                    num_icon    = "✓" if is_done else str(step['step_number'])
                    xp_val      = 5 if is_done else (10 if is_active else 5)
                    xp_cls      = "done" if is_done else ""
                    text_cls    = "done" if is_done else ""

                    # Render HTML card
                    st.markdown(
                        f'<div class="quest-step {css_cls}">'
                        f'<div class="quest-num {num_cls}">{num_icon}</div>'
                        f'<div class="quest-text {text_cls}">{step["content"]}</div>'
                        f'<div class="quest-xp {xp_cls}">+{xp_val} XP</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                    # Interaktiver Toggle — aktive Steps
                    if is_active or is_done:
                        chk_col, _ = st.columns([0.12, 0.88])
                        with chk_col:
                            checked = st.checkbox(
                                " ", value=is_done,
                                key=f"fstep_{step['id']}_{round_num}"
                            )
                            if checked != is_done:
                                toggle_step(step['id'], checked)
                                for s in st.session_state.focus_steps:
                                    if s['id'] == step['id']:
                                        s['done'] = checked
                                st.rerun()

                # Mission Complete Banner
                if all_done:
                    st.markdown(
                        '<div class="mission-complete">'
                        '<div style="font-size:28px;margin-bottom:4px">🏆</div>'
                        '<div style="font-size:16px;font-weight:900;color:#2ecc71">MISSION COMPLETE</div>'
                        '<div style="font-size:11px;color:rgba(255,255,255,0.5);margin-top:4px">'
                        'Alle Ziele erreicht! Aufgabe als fertig markieren.</div>'
                        '</div>',
                        unsafe_allow_html=True
                    )

                st.markdown('</div>', unsafe_allow_html=True)

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

        # ── Action-Buttons: Micro | Kategorie | Bearbeiten | Löschen ──
        if not done:
            bc1, bc2, bc3, bc4 = st.columns(4)
            with bc1:
                micro_lbl = "⚡ Micro ändern" if micro_action else "⚡ Micro setzen"
                if st.button(micro_lbl, key=f"{pfx}_mshow_{eid}", use_container_width=True):
                    st.session_state[f"show_micro_{eid}"] = not st.session_state.get(f"show_micro_{eid}", False)
                    st.rerun()
            with bc2:
                if show_category_controls:
                    cat_lbl = f"🏷️ {cat['icon']} {cat['name']}" if cat else "🏷️ Kategorie"
                    if st.button(cat_lbl, key=f"{pfx}_cshow_{eid}", use_container_width=True):
                        st.session_state[f"show_cat_{eid}"] = not st.session_state.get(f"show_cat_{eid}", False)
                        st.rerun()
            with bc3:
                edit_open = st.session_state.get(f"edit_open_{eid}", False)
                if st.button("✏️ Bearbeiten" if not edit_open else "✕ Schließen",
                             key=f"{pfx}_editbtn_{eid}", use_container_width=True):
                    st.session_state[f"edit_open_{eid}"] = not edit_open
                    st.rerun()
            with bc4:
                if st.button("🗑️ Löschen", key=f"{pfx}_del_{eid}", use_container_width=True):
                    delete_entry(eid)
                    st.rerun()

            # ── Micro-Eingabe ──────────────────────────────────────
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

            # ── Kategorie-Auswahl ──────────────────────────────────
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

            # ── Inline-Bearbeiten-Formular ─────────────────────────
            if st.session_state.get(f"edit_open_{eid}"):
                st.markdown(
                    '<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.1);'
                    'border-radius:10px;padding:14px 16px;margin-top:6px">',
                    unsafe_allow_html=True
                )
                ef1, ef2 = st.columns([3, 1])
                with ef1:
                    edit_content = st.text_input(
                        "Aufgabe", value=content,
                        key=f"{pfx}_econtent_{eid}"
                    )
                with ef2:
                    edit_est = st.number_input(
                        "Minuten", value=int(estimate or 0), min_value=0, max_value=480,
                        key=f"{pfx}_eest_{eid}"
                    )
                ef3, ef4 = st.columns(2)
                with ef3:
                    edit_tags = st.text_input(
                        "Tags (kommagetrennt)", value=tags or "",
                        key=f"{pfx}_etags_{eid}"
                    )
                with ef4:
                    dl_val = None
                    if deadline:
                        try:
                            dl_val = date.fromisoformat(deadline)
                        except Exception:
                            pass
                    edit_dl = st.date_input(
                        "Deadline (optional)", value=dl_val,
                        key=f"{pfx}_edl_{eid}"
                    )
                esave, ecancel = st.columns(2)
                with esave:
                    if st.button("💾 Änderungen speichern", key=f"{pfx}_esave_{eid}", use_container_width=True, type="primary"):
                        dl_str = edit_dl.isoformat() if edit_dl else None
                        conn_e = sqlite3.connect(DB_PATH)
                        conn_e.execute(
                            "UPDATE entries SET content=?, estimate_minutes=?, tags=?, deadline=? WHERE id=?",
                            (edit_content.strip() or content,
                             int(edit_est) if edit_est else None,
                             edit_tags.strip() or None,
                             dl_str, eid)
                        )
                        conn_e.commit()
                        conn_e.close()
                        st.session_state[f"edit_open_{eid}"] = False
                        st.rerun()
                with ecancel:
                    if st.button("✕ Abbrechen", key=f"{pfx}_ecancel_{eid}", use_container_width=True):
                        st.session_state[f"edit_open_{eid}"] = False
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

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

    tab_hl, tab_todo, tab_close = st.tabs([
        f"⭐ Highlight ({open_hl} offen)",
        f"📝 To-Do Liste ({open_todos} offen)",
        "🌙 Tag abschließen"
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

    # ── TAB 3: TAG ABSCHLIEßEN ───────────────────────────────────────
    with tab_close:
        today_str = date.today().isoformat()
        api_key   = get_setting('nvidia_api_key', '')
        already_closed = bool(get_journal_entry(today_str))

        # ── Hero ────────────────────────────────────────────────────
        pct_display = int(pct * 100)
        bar_col = "#e74c3c" if pct_display < 30 else "#f39c12" if pct_display < 65 else "#2ecc71"
        st.markdown(f"""
<div style="background:linear-gradient(135deg,rgba(155,89,182,0.12) 0%,rgba(0,0,0,0) 100%);
            border:1px solid rgba(155,89,182,0.25);border-radius:16px;padding:20px 24px;margin-bottom:18px">
  <div style="font-size:11px;color:rgba(255,255,255,0.4);letter-spacing:3px;
              text-transform:uppercase;margin-bottom:10px">🌙 Tagesabschluss</div>
  <div style="display:flex;align-items:center;gap:24px">
    <div style="text-align:center">
      <div style="font-size:36px;font-weight:900;color:{bar_col}">{pct_display}%</div>
      <div style="font-size:10px;color:rgba(255,255,255,0.35)">erledigt</div>
    </div>
    <div style="flex:1">
      <div style="display:flex;justify-content:space-between;font-size:11px;
                  color:rgba(255,255,255,0.45);margin-bottom:5px">
        <span>✅ {done_count} erledigt</span><span>⏳ {total - done_count} offen</span>
      </div>
      <div style="background:rgba(255,255,255,0.1);border-radius:4px;height:6px;overflow:hidden">
        <div style="width:{pct_display}%;height:100%;background:{bar_col};border-radius:4px"></div>
      </div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

        # ── 1. KI-Tagesreview ───────────────────────────────────────
        st.markdown("#### 🤖 KI-Tagesreview")
        if api_key:
            if st.button("🌙 Tag abschließen & KI-Review erstellen", key="tc_ki_review",
                         use_container_width=True, type="primary"):
                with st.spinner("KI analysiert deinen Tag …"):
                    rv = ki_evening_review(api_key)
                st.session_state['tc_review'] = rv
                st.rerun()

            if 'tc_review' in st.session_state:
                rv = st.session_state['tc_review']
                if 'error' in rv:
                    st.error(f"Fehler: {rv['error']}")
                else:
                    st.markdown(f"**{rv.get('headline', 'Tagesrückblick')}**")
                    wins = rv.get('wins', [])
                    if wins:
                        for w in wins:
                            st.markdown(f"- 🏆 {w}")
                    if rv.get('open_note'):
                        st.info(f"📝 {rv['open_note']}")
                    for alert in rv.get('upcoming_alerts', []):
                        st.warning(alert)
                    if rv.get('optimization_tip'):
                        st.success(f"💡 **Morgen:** {rv['optimization_tip']}")
                    if rv.get('tomorrow_focus'):
                        st.markdown(f"🎯 Fokus morgen: **{rv['tomorrow_focus']}**")
                    if rv.get('motivation'):
                        st.caption(f"*{rv['motivation']}*")
        else:
            st.caption("Kein API-Key hinterlegt — KI-Review in den Einstellungen aktivieren.")

        st.markdown("---")

        # ── 2. Spontane Gedanken sortieren ──────────────────────────
        unsorted = get_unsorted_thoughts()
        if unsorted:
            st.markdown(f"#### 💭 Spontane Gedanken sortieren ({len(unsorted)})")
            st.caption("Diese Gedanken hast du heute festgehalten — was passiert damit?")
            tomorrow_str = (date.today() + timedelta(days=1)).isoformat()
            for th in unsorted:
                th_id, th_content, th_created = th['id'], th['content'], th['created_at']
                with st.container(border=True):
                    st.markdown(f"**{th_content}**")
                    if th_created:
                        try:
                            ts = datetime.fromisoformat(th_created).strftime("%H:%M")
                            st.caption(f"notiert um {ts}")
                        except Exception:
                            pass
                    sc1, sc2, sc3 = st.columns(3)
                    with sc1:
                        if st.button("✅ Heute", key=f"tc_sp_today_{th_id}", use_container_width=True):
                            resolve_thought_to_entry(th_id, th_content, today_str)
                            st.toast("Als Aufgabe für heute angelegt ✓", icon="✅")
                            st.rerun()
                    with sc2:
                        if st.button("➡️ Morgen", key=f"tc_sp_tmrw_{th_id}", use_container_width=True):
                            resolve_thought_to_entry(th_id, th_content, tomorrow_str)
                            st.toast("Als Aufgabe für morgen angelegt ✓", icon="➡️")
                            st.rerun()
                    with sc3:
                        if st.button("🗑️ Verwerfen", key=f"tc_sp_disc_{th_id}", use_container_width=True):
                            discard_thought(th_id)
                            st.toast("Verworfen ✓", icon="🗑️")
                            st.rerun()
            st.markdown("---")

        # ── 3. Manuelle Tagesreflexion ──────────────────────────────
        st.markdown("#### 📓 Tagesreflexion")
        existing_entry = get_journal_entry(today_str)
        journal_nonce = st.session_state.get('journal_nonce', 0)
        journal_text  = st.text_area(
            "Reflexion", key=f"tc_journal_{journal_nonce}",
            value=existing_entry,
            label_visibility="collapsed",
            placeholder="Was lief heute gut? Was nehme ich mit? Was war schwierig?\n\nFreier Brain-Dump — kein Druck, keine Regeln.",
            height=160
        )
        tc1, tc2 = st.columns([3, 1])
        with tc1:
            if st.button("💾 Reflexion speichern", key="tc_journal_save", use_container_width=True):
                if journal_text and journal_text.strip():
                    save_journal_entry(journal_text.strip())
                    st.session_state['journal_nonce'] = journal_nonce + 1
                    st.toast("Reflexion gespeichert ✓", icon="📓")
                    st.rerun()
        with tc2:
            if existing_entry:
                st.success("✓ gespeichert")

        st.markdown("---")

        # ── 4. Abendroutine ─────────────────────────────────────────
        st.markdown("#### 🌙 Abendroutine")
        checks_pm = get_routine_checks(today_str, 'evening')
        done_pm = sum(1 for t in EVENING_ROUTINE_TASKS if checks_pm.get(t['key'], False))
        st.caption(f"{done_pm}/{len(EVENING_ROUTINE_TASKS)} erledigt")
        render_evening_routine_checklist(today_str)

        st.markdown("---")
        if st.button("😴 Zur Schlaf-Seite →", key="tc_goto_sleep", use_container_width=True):
            st.session_state.page = "Schlaf"
            st.rerun()


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
    st.caption("Ein Projekt, ein Task pro Tag — kein Chaos, nur Fortschritt.")

    with st.expander("➕ Neues Projekt erstellen", expanded=False):
        with st.form("new_project_form"):
            name = st.text_input("Projektname", placeholder="z.B. Video-Kurs Trading erstellen")
            roter_faden = st.text_area(
                "Roter Faden",
                height=70,
                placeholder="Was ist das Kernziel? Welchen Ansatz verfolgst du? Was soll am Ende stehen?\nz.B. 'Schritt-für-Schritt Video-Kurs mit je 1 Video pro Session — immer mit Skript beginnen, dann aufnehmen.'"
            )
            description = st.text_area("Beschreibung / Kontext (optional)", height=50)
            col1, col2, col3 = st.columns(3)
            with col1:
                deadline = st.date_input("Deadline", value=date.today() + timedelta(days=30))
            with col2:
                daily_minutes = st.number_input("Fokus-Zeit/Tag (Min)", min_value=15, step=15, value=60)
            with col3:
                color = st.color_picker("Projektfarbe", value="#60a5fa")
            if st.form_submit_button("Projekt anlegen", use_container_width=True):
                if name.strip():
                    pid = add_project(name.strip(), description.strip(), deadline.isoformat(),
                                      color, daily_minutes, roter_faden.strip())
                    st.session_state.selected_project = pid
                    st.rerun()

    st.markdown("---")
    projects = get_projects()
    if not projects:
        st.info("Noch keine Projekte — erstelle dein erstes Projekt oben.")
        return

    today_str = date.today().isoformat()

    for proj in projects:
        pid, name, description, deadline, color, active, created_at, daily_minutes, roter_faden = proj
        tasks = get_project_tasks(pid)
        total = len(tasks)
        done_c = sum(1 for t in tasks if t[5])
        pct = done_c / total if total > 0 else 0
        _, _, urg_label, _ = get_urgency(deadline)

        # Heutiger Task aus project_tasks
        today_proj_task = next(
            (t for t in tasks if not t[5] and t[7] == today_str), None
        )
        next_undone = next((t for t in tasks if not t[5]), None)

        # Fortschritt-Farbe
        if pct >= 0.8:
            bar_color = '#2ecc71'
        elif pct >= 0.4:
            bar_color = '#f39c12'
        else:
            bar_color = color

        today_html = ""
        if today_proj_task:
            today_html = (
                f'<div style="display:flex;align-items:center;gap:8px;margin-top:10px;'
                f'background:{color}15;border-radius:8px;padding:8px 12px">'
                f'<span style="font-size:11px;font-weight:800;color:{color}">HEUTE</span>'
                f'<span style="font-size:12.5px;color:rgba(255,255,255,0.85)">{today_proj_task[2]}</span>'
                f'<span style="font-size:10px;color:rgba(255,255,255,0.35);margin-left:auto">⏱️ {today_proj_task[3] or 30} min</span>'
                f'</div>'
            )
        elif next_undone:
            today_html = (
                f'<div style="font-size:11px;color:rgba(255,255,255,0.4);margin-top:8px">'
                f'Nächste: {next_undone[2]}</div>'
            )
        elif total > 0:
            today_html = '<div style="font-size:11px;color:#2ecc71;margin-top:8px">✅ Alle Aufgaben erledigt!</div>'

        faden_html = (
            f'<div style="font-size:11px;color:rgba(255,255,255,0.45);margin-top:4px;font-style:italic">'
            f'🧵 {roter_faden[:120]}{"…" if len(roter_faden)>120 else ""}</div>'
        ) if roter_faden else ''

        st.markdown(
            f'<div style="border-left:4px solid {color};background:rgba(255,255,255,0.03);'
            f'border-radius:12px;padding:16px 20px;margin-bottom:6px">'
            f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">'
            f'<strong style="font-size:17px;color:white">{name}</strong>'
            + (f'<span class="dl-badge">{urg_label}</span>' if urg_label else
               (f'<span class="dl-badge">📅 {deadline}</span>' if deadline else ''))
            + f'<span class="dl-badge">⏱️ {daily_minutes} min/Tag</span>'
            + f'</div>'
            + f'{faden_html}'
            + f'<div style="font-size:11px;color:rgba(255,255,255,0.4);margin-top:6px">{done_c}/{total} Aufgaben · {int(pct*100)}%</div>'
            + today_html
            + '</div>',
            unsafe_allow_html=True
        )

        # Fortschrittsbalken
        bar_w = int(pct * 100)
        st.markdown(
            f'<div style="height:4px;background:rgba(255,255,255,0.07);border-radius:2px;margin:-4px 0 10px 0">'
            f'<div style="width:{bar_w}%;height:100%;background:{bar_color};border-radius:2px;'
            f'transition:width 0.4s"></div></div>',
            unsafe_allow_html=True
        )

        c1, c2, _ = st.columns([0.16, 0.12, 0.72])
        with c1:
            if st.button("Öffnen →", key=f"proj_open_{pid}", use_container_width=True):
                st.session_state.selected_project = pid
                st.rerun()
        with c2:
            if st.button("🗑️", key=f"proj_del_{pid}", use_container_width=True):
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
    c.execute('''SELECT id, name, description, deadline, color, active, created_at, daily_minutes,
                        COALESCE(roter_faden,'')
                 FROM projects WHERE id=?''', (project_id,))
    proj = c.fetchone()
    conn.close()
    if not proj:
        st.session_state.selected_project = None
        st.rerun()
        return

    pid, name, description, deadline, color, active, created_at, daily_minutes, roter_faden = proj

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

    # ── Header ──────────────────────────────────────────────────────
    st.markdown(f'<h2 style="color:{color};margin-bottom:4px">{name}</h2>', unsafe_allow_html=True)

    if roter_faden:
        st.markdown(
            f'<div style="background:{color}10;border-left:3px solid {color};border-radius:0 10px 10px 0;'
            f'padding:12px 16px;margin-bottom:12px">'
            f'<div style="font-size:10px;color:rgba(255,255,255,0.35);letter-spacing:1.5px;'
            f'text-transform:uppercase;margin-bottom:4px">ROTER FADEN</div>'
            f'<div style="font-size:13px;color:rgba(255,255,255,0.8);font-style:italic">{roter_faden}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    if description:
        st.caption(description)

    # ── Today's task banner ──────────────────────────────────────────
    today_str = date.today().isoformat()
    today_proj_task = next((t for t in tasks if not t[5] and t[7] == today_str), None)
    if today_proj_task:
        st.markdown(
            f'<div style="background:linear-gradient(135deg,{color}20,{color}08);'
            f'border:1px solid {color}44;border-radius:12px;padding:14px 18px;margin-bottom:12px">'
            f'<div style="font-size:10px;font-weight:800;color:{color};letter-spacing:1.5px;'
            f'text-transform:uppercase;margin-bottom:6px">HEUTE DRAN</div>'
            f'<div style="font-size:14px;font-weight:700;color:white">{today_proj_task[2]}</div>'
            + (f'<div style="font-size:11px;color:rgba(255,255,255,0.4);margin-top:4px">⏱️ {today_proj_task[3]} min geplant</div>' if today_proj_task[3] else '')
            + '</div>',
            unsafe_allow_html=True
        )

    # ── Stats ──────────────────────────────────────────────────────
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Aufgaben", f"{done_count} / {total}")
    mc2.metric("Fortschritt", f"{int(pct*100)} %")
    mc3.metric("Zeit erledigt", f"{done_mins} min")
    if days_left is not None:
        mc4.metric("Tage bis Deadline", days_left, delta=None)

    bar_w = int(pct * 100)
    st.markdown(
        f'<div style="height:6px;background:rgba(255,255,255,0.07);border-radius:3px;margin:4px 0 12px 0">'
        f'<div style="width:{bar_w}%;height:100%;background:{color};border-radius:3px"></div></div>',
        unsafe_allow_html=True
    )

    if days_left is not None and days_left >= 0:
        undone = [t for t in tasks if not t[5]]
        if undone:
            remaining_mins = sum(t[3] or 0 for t in undone)
            needed = remaining_mins / max(days_left, 1)
            if days_left <= 3:
                st.warning(f"⏰ Nur noch {days_left} Tage! Ca. {int(needed)} min/Tag nötig.")
            elif int(needed) > daily_minutes:
                st.warning(f"📊 {int(needed)} min/Tag nötig — mehr als die geplanten {daily_minutes} min/Tag.")
    elif days_left is not None and days_left < 0:
        st.error(f"⚠️ Deadline überschritten! Noch {sum(t[3] or 0 for t in tasks if not t[5])} min offen.")

    st.markdown("---")

    # ── Einstellungen ──────────────────────────────────────────────
    if st.button("⚙️ Projekteinstellungen", use_container_width=False, key="proj_settings_btn"):
        st.session_state[f'proj_settings_{pid}'] = not st.session_state.get(f'proj_settings_{pid}', False)
        st.rerun()

    if st.session_state.get(f'proj_settings_{pid}'):
        with st.form("edit_project_form"):
            new_name = st.text_input("Name", value=name)
            new_faden = st.text_area("Roter Faden", value=roter_faden or "", height=80)
            new_desc = st.text_area("Beschreibung", value=description or "", height=50)
            c1, c2, c3 = st.columns(3)
            with c1:
                new_deadline = st.date_input("Deadline",
                    value=date.fromisoformat(deadline) if deadline else date.today())
            with c2:
                new_daily = st.number_input("Min/Tag", min_value=15, step=15, value=daily_minutes or 60)
            with c3:
                new_color = st.color_picker("Farbe", value=color or "#60a5fa")
            if st.form_submit_button("Speichern"):
                conn2 = sqlite3.connect(DB_PATH)
                conn2.execute(
                    'UPDATE projects SET name=?, description=?, deadline=?, daily_minutes=?, color=?, roter_faden=? WHERE id=?',
                    (new_name, new_desc, new_deadline.isoformat(), new_daily, new_color, new_faden.strip(), pid)
                )
                conn2.commit()
                conn2.close()
                st.session_state[f'proj_settings_{pid}'] = False
                st.rerun()

    # ── Task-Liste ────────────────────────────────────────────────

    # Aufgabe hinzufügen
    with st.expander("➕ Aufgabe hinzufügen", expanded=False):
        with st.form("add_task_form"):
            task_content = st.text_input("Was muss gemacht werden?",
                                          placeholder="Konkret und umsetzbar formulieren")
            col1, col2 = st.columns(2)
            with col1:
                task_estimate = st.number_input("Minuten", min_value=5, step=5, value=30)
            with col2:
                task_priority = st.slider("Priorität", min_value=0, max_value=10, value=5)
            task_notes = st.text_area("Notizen (optional)", height=60,
                                       placeholder="Kontext, Links, Gedanken...")
            if st.form_submit_button("Aufgabe hinzufügen", use_container_width=True):
                if task_content.strip():
                    add_project_task(pid, task_content.strip(), task_estimate, task_priority)
                    if task_notes.strip():
                        conn_n = sqlite3.connect(DB_PATH)
                        last_id = conn_n.execute("SELECT MAX(id) FROM project_tasks WHERE project_id=?", (pid,)).fetchone()[0]
                        if last_id:
                            conn_n.execute("UPDATE project_tasks SET notes=? WHERE id=?", (task_notes.strip(), last_id))
                            conn_n.commit()
                        conn_n.close()
                    st.rerun()

    undone_tasks = [t for t in tasks if not t[5]]
    done_tasks   = [t for t in tasks if t[5]]

    PRESET_COLORS = [
        ("Kein", ""), ("🟡", "#ffd700"), ("🔴", "#e74c3c"), ("🟢", "#2ecc71"),
        ("🔵", "#3498db"), ("🟣", "#9b59b6"), ("🟠", "#f39c12"),
    ]

    if undone_tasks:
        st.markdown(f"**📋 Aufgaben ({len(undone_tasks)} offen)**")
        for i, t in enumerate(undone_tasks):
            task_id, _, content, estimate, priority, done, completed_at, scheduled_date, order_idx, notes, hl_color = t
            is_today  = scheduled_date == today_str
            border_c  = hl_color if hl_color else (color if is_today else 'rgba(255,255,255,0.12)')
            card_bg   = f"{hl_color}12" if hl_color else (f"{color}12" if is_today else "rgba(255,255,255,0.02)")
            edit_open = st.session_state.get(f"pt_edit_{task_id}", False)

            today_badge = (
                f'<span style="font-size:9px;font-weight:800;color:{color};background:{color}18;'
                f'border:1px solid {color}44;padding:2px 7px;border-radius:5px;margin-left:8px">HEUTE</span>'
            ) if is_today else ''
            date_badge = (
                f'<span class="dl-badge">{scheduled_date}</span>'
                if scheduled_date and not is_today else ''
            )
            notes_preview = (
                f'<div style="font-size:11px;color:rgba(255,255,255,.4);margin-top:5px;'
                f'white-space:pre-wrap;border-left:2px solid rgba(255,255,255,.12);padding-left:8px">'
                f'{notes[:200]}{"…" if len(notes) > 200 else ""}</div>'
            ) if notes and not edit_open else ''

            st.markdown(
                f'<div style="border-left:3px solid {border_c};background:{card_bg};'
                f'border-radius:0 10px 10px 0;padding:10px 14px;margin-bottom:3px">'
                f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px">'
                f'<strong style="font-size:13.5px">{content}</strong>'
                f'{today_badge}{date_badge}'
                + (f'<span class="dl-badge">⏱️ {estimate} min</span>' if estimate else '')
                + f'</div>{notes_preview}</div>',
                unsafe_allow_html=True
            )

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
                if i < len(undone_tasks) - 1 and st.button("↓", key=f"pt_dn_{task_id}", use_container_width=True):
                    move_project_task(task_id, 1, pid)
                    st.rerun()
            with cedit:
                if st.button("✕ Schließen" if edit_open else "✏️ Bearbeiten",
                             key=f"pt_editbtn_{task_id}", use_container_width=True):
                    st.session_state[f"pt_edit_{task_id}"] = not edit_open
                    st.rerun()
            with cdel:
                if st.button("🗑️", key=f"pt_del_{task_id}", use_container_width=True):
                    delete_project_task(task_id)
                    st.session_state.pop(f"pt_edit_{task_id}", None)
                    st.rerun()

            if edit_open:
                with st.form(f"pt_edit_form_{task_id}"):
                    new_content = st.text_input("Aufgabe", value=content, key=f"pe_cnt_{task_id}")
                    ea, eb, ec = st.columns(3)
                    with ea:
                        new_est = st.number_input("⏱️ Minuten", min_value=1, step=5,
                                                   value=int(estimate or 30), key=f"pe_est_{task_id}")
                    with eb:
                        new_prio = st.slider("Priorität", 0, 10, value=int(priority or 5),
                                             key=f"pe_prio_{task_id}")
                    with ec:
                        try:
                            sd_val = date.fromisoformat(scheduled_date) if scheduled_date else date.today()
                        except Exception:
                            sd_val = date.today()
                        new_date = st.date_input("📅 Einplanen für", value=sd_val, key=f"pe_date_{task_id}")
                    color_labels = [p[0] for p in PRESET_COLORS]
                    cur_color_idx = next((i for i, p in enumerate(PRESET_COLORS) if p[1] == hl_color), 0)
                    chosen_label = st.radio("Farbe", color_labels, index=cur_color_idx,
                                            horizontal=True, label_visibility="collapsed",
                                            key=f"pe_color_{task_id}")
                    chosen_color = next((p[1] for p in PRESET_COLORS if p[0] == chosen_label), "")
                    new_notes = st.text_area("📝 Notizen", value=notes or "", height=100,
                                             placeholder="Gedanken, Links, Zwischenstände...",
                                             key=f"pe_notes_{task_id}")
                    fs, fc = st.columns(2)
                    with fs:
                        if st.form_submit_button("💾 Speichern", use_container_width=True):
                            update_project_task(task_id, new_content.strip(), new_est, new_prio,
                                                new_notes.strip(), chosen_color, new_date.isoformat())
                            st.session_state.pop(f"pt_edit_{task_id}", None)
                            st.rerun()
                    with fc:
                        if st.form_submit_button("✕ Abbrechen", use_container_width=True):
                            st.session_state.pop(f"pt_edit_{task_id}", None)
                            st.rerun()

            st.markdown('<div style="margin-bottom:2px"></div>', unsafe_allow_html=True)
    else:
        if total == 0:
            st.info("Noch keine Aufgaben — füge deine erste Aufgabe oben hinzu.")
        else:
            st.success("Alle Aufgaben erledigt!")

    if done_tasks:
        with st.expander(f"✅ Erledigt ({len(done_tasks)})"):
            for t in done_tasks:
                task_id, _, content, estimate, priority, done_val, completed_at, scheduled_date, order_idx, notes, hl_color = t
                st.markdown(
                    f'<div style="opacity:.4;text-decoration:line-through;padding:4px 0;font-size:13px">'
                    f'{content}</div>',
                    unsafe_allow_html=True
                )
                c1, _ = st.columns([0.10, 0.90])
                with c1:
                    if not st.checkbox("", value=True, key=f"pt_chk_{task_id}",
                                       label_visibility="collapsed"):
                        toggle_project_task_done(task_id, False)
                        st.rerun()

    # ── Visualizations ────────────────────────────────────────────────────────
    if tasks:
        st.markdown("---")
        st.subheader("📊 Fortschritt")

        tab1, tab2, tab3 = st.tabs(["Burndown", "Gantt", "🔮 Prognose"])

        with tab1:
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
                        line=dict(color=color, width=3),
                        fill='tozeroy', fillcolor=f'{color}18'
                    ))
                    fig_b.add_hline(y=total, line_dash="dash", line_color="rgba(255,255,255,0.3)",
                                     annotation_text=f"Gesamt: {total}")
                    fig_b.update_layout(template='plotly_dark', showlegend=False,
                                         yaxis_title="Aufgaben erledigt")
                    st.plotly_chart(fig_b, use_container_width=True)
            else:
                st.info("Erledige Aufgaben um den Fortschritt zu sehen.")

        with tab2:
            gantt_data = []
            for t in tasks:
                task_id, _, content, estimate, priority, done_val, completed_at, scheduled_date, _, _, _ = t
                if scheduled_date:
                    try:
                        start_dt = datetime.combine(date.fromisoformat(scheduled_date), datetime.min.time())
                        end_dt = start_dt + timedelta(minutes=max(estimate or 30, 15))
                        gantt_data.append({
                            'Aufgabe': (content[:40] + '…') if len(content) > 40 else content,
                            'Start': start_dt.strftime('%Y-%m-%d %H:%M:%S'),
                            'Ende':  end_dt.strftime('%Y-%m-%d %H:%M:%S'),
                            'Status': 'Erledigt' if done_val else 'Offen',
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
                fig_g.add_vline(
                    x=datetime.combine(date.today(), datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S'),
                    line_dash="dash", line_color="#ffd700",
                    annotation_text="Heute", annotation_font_color="#ffd700"
                )
                if deadline:
                    try:
                        fig_g.add_vline(
                            x=datetime.combine(date.fromisoformat(deadline), datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S'),
                            line_dash="dot", line_color="#ef4444",
                            annotation_text="Deadline", annotation_font_color="#ef4444"
                        )
                    except Exception:
                        pass
                st.plotly_chart(fig_g, use_container_width=True)
            else:
                st.info("Tasks werden hier angezeigt sobald sie einen Termin haben.")

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


_KI_STATS_SYSTEM = """Du bist ein datengetriebener Produktivitäts-Analyst mit ADHS-Coaching-Expertise.
Analysiere die Statistikdaten und liefere präzise, actionable Insights auf Deutsch.

DEINE ANALYSE MUSS:
1. MUSTER erkennen — positiv UND negativ, mit konkreten Zahlen
2. PROBLEME identifizieren — was funktioniert NICHT, mit Datenbeweis
3. LÖSUNGEN liefern — spezifisch, umsetzbar, mit Zeitangaben
4. KORRELATIONEN aufdecken — welche Faktoren beeinflussen was?

STIL für ADHS-Coaching:
- Direkt und ohne Floskeln
- Konkrete Uhrzeiten, Prozente, Zahlen nennen
- Keine allgemeinen Ratschläge — NUR was die Daten zeigen

OUTPUT: Nur valides JSON:
{
  "top_pattern": "Ein Satz — das wichtigste Muster mit konkreten Daten",
  "patterns": [
    {"icon": "emoji", "title": "Kurztitel", "evidence": "Konkrete Datenbasis mit Zahlen", "type": "positive|neutral|negative"}
  ],
  "problems": [
    {"title": "Problemtitel", "evidence": "Daten-Beweis mit Zahlen", "severity": "hoch|mittel|niedrig", "icon": "emoji"}
  ],
  "solutions": [
    {"problem": "Auf welches Problem bezogen", "action": "Konkrete Aktion mit Uhrzeit/Zahl", "why": "Daten-Begründung", "icon": "emoji"}
  ],
  "correlations": [
    {"factor_a": "...", "factor_b": "...", "insight": "Was die Daten zeigen", "icon": "emoji"}
  ],
  "energy_insight": "Optimale Tagesstruktur in 2-3 Sätzen basierend auf den Daten"
}"""


def ki_analyze_statistics(api_key):
    """KI analysiert alle Statistikdaten: Muster, Probleme, Lösungen, Korrelationen."""
    conn = sqlite3.connect(DB_PATH)

    hour_data = conn.execute("""
        SELECT CAST(strftime('%H', completed_at) AS INTEGER) as h,
               COUNT(*) as n, AVG(elapsed_seconds) as avg_secs
        FROM entries WHERE done=1 AND completed_at IS NOT NULL
        GROUP BY h ORDER BY h
    """).fetchall()

    wd_data = conn.execute("""
        SELECT strftime('%w', entry_date) as wd,
               COUNT(*) as tasks, ROUND(AVG(done)*100,0) as done_rate
        FROM entries WHERE entry_date >= date('now','-60 days') GROUP BY wd
    """).fetchall()

    start_times = conn.execute("""
        SELECT entry_date, strftime('%H:%M', MIN(started_at)) as first_start, COUNT(*) as tasks_done
        FROM entries WHERE done=1 AND started_at IS NOT NULL
        AND entry_date >= date('now','-30 days')
        GROUP BY entry_date ORDER BY entry_date DESC LIMIT 20
    """).fetchall()

    sleep_prod = conn.execute("""
        SELECT s.quality_pct,
               (SELECT COUNT(*) FROM entries e WHERE e.entry_date = date(s.log_date,'+1 day') AND e.done=1) as tasks_next
        FROM sleep_logs s WHERE s.log_date >= date('now','-30 days') AND s.quality_pct IS NOT NULL
    """).fetchall()

    sleep_avg = conn.execute(
        "SELECT AVG(quality_pct) FROM sleep_logs WHERE log_date >= date('now','-30 days')"
    ).fetchone()[0]

    habit_cons = conn.execute("""
        SELECT h.name,
               COALESCE(SUM(CASE WHEN hl.log_date >= date('now','-30 days') THEN 1 ELSE 0 END),0) as last_30,
               COALESCE(SUM(CASE WHEN hl.log_date >= date('now','-7 days') THEN 1 ELSE 0 END),0) as last_7
        FROM habits h LEFT JOIN habit_logs hl ON h.id = hl.habit_id GROUP BY h.id
    """).fetchall()

    routine_adh = conn.execute("""
        SELECT routine, ROUND(AVG(done)*100,0) as avg_pct
        FROM routine_checks WHERE log_date >= date('now','-30 days') GROUP BY routine
    """).fetchall()

    train_cons = conn.execute("""
        SELECT COUNT(DISTINCT session_date) as days, ROUND(AVG(clean)*100,0) as clean_pct
        FROM cal_sessions WHERE session_date >= date('now','-30 days')
    """).fetchone()

    est_acc = conn.execute("""
        SELECT AVG((elapsed_seconds/60.0 - estimate_minutes) / NULLIF(estimate_minutes,0) * 100) as avg_err
        FROM entries WHERE done=1 AND estimate_minutes > 0 AND elapsed_seconds > 30
    """).fetchone()

    weekly_rate = conn.execute("""
        SELECT strftime('%Y-W%W', entry_date) as week,
               ROUND(AVG(done)*100,0) as rate, COUNT(*) as tasks
        FROM entries WHERE entry_date >= date('now','-60 days')
        GROUP BY week ORDER BY week
    """).fetchall()

    dur_stats = conn.execute("""
        SELECT AVG(elapsed_seconds)/60.0 as avg_min,
               COUNT(CASE WHEN elapsed_seconds < 300 THEN 1 END) as unter5,
               COUNT(CASE WHEN elapsed_seconds >= 1800 THEN 1 END) as ueber30
        FROM entries WHERE done=1 AND elapsed_seconds > 30
    """).fetchone()

    conn.close()

    wd_names = {0:'So',1:'Mo',2:'Di',3:'Mi',4:'Do',5:'Fr',6:'Sa'}
    peak_hours = sorted(hour_data, key=lambda x: x[1], reverse=True)[:3]
    summary = {
        "produktivitaet_nach_stunde": [
            {"stunde": r[0], "aufgaben": r[1], "avg_min": round((r[2] or 0)/60,1)} for r in hour_data
        ],
        "peak_stunden": [f"{r[0]}h ({r[1]} Aufg.)" for r in peak_hours],
        "wochentag_aufgaben": [
            {"tag": wd_names.get(int(r[0]),'?'), "aufgaben": r[1], "rate_pct": r[2]} for r in wd_data
        ],
        "tagesstart_muster": [
            {"datum": r[0], "erste_aufgabe": r[1], "aufgaben_erledigt": r[2]} for r in start_times[:10]
        ],
        "schlaf_prod_korrelation": [
            {"schlaf_pct": r[0], "aufgaben_folgetag": r[1]} for r in sleep_prod
        ],
        "schlaf_avg_pct": round(sleep_avg or 0, 0),
        "habits": [
            {"name": r[0], "30d_von_30": r[1], "7d_von_7": r[2]} for r in habit_cons
        ],
        "routinen": [{"routine": r[0], "adhaerenz_pct": r[1]} for r in routine_adh],
        "training_30d": {
            "trainingstage": train_cons[0] if train_cons else 0,
            "clean_rate_pct": train_cons[1] if train_cons else 0
        },
        "schaetzfehler_avg_pct": round(est_acc[0] or 0, 1) if est_acc and est_acc[0] else None,
        "wochentliche_rate": [{"woche": r[0], "rate_pct": r[1]} for r in weekly_rate],
        "session_stats": {
            "avg_min": round(dur_stats[0] or 0, 1) if dur_stats else 0,
            "unter_5min": dur_stats[1] if dur_stats else 0,
            "ueber_30min": dur_stats[2] if dur_stats else 0,
        }
    }

    try:
        from openai import OpenAI
        client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=api_key)
        resp = client.chat.completions.create(
            model=KIMI_MODEL,
            messages=[
                {"role": "system", "content": _KI_STATS_SYSTEM},
                {"role": "user", "content": f"Analysiere diese Statistikdaten:\n\n{json.dumps(summary, ensure_ascii=False, indent=2)}"}
            ],
            temperature=0.35, max_tokens=2500
        )
        return _parse_ki_json(resp.choices[0].message.content)
    except Exception as e:
        return {"error": str(e)}


def render_statistics_page():
    st.title("📊 Statistiken")

    conn = sqlite3.connect(DB_PATH)

    # ── Alle Kern-KPIs laden ───────────────────────────────────────
    total       = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    done        = conn.execute("SELECT COUNT(*) FROM entries WHERE done=1").fetchone()[0]
    total_secs  = conn.execute("SELECT COALESCE(SUM(elapsed_seconds),0) FROM entries WHERE done=1").fetchone()[0]
    active_30   = conn.execute("SELECT COUNT(DISTINCT DATE(completed_at)) FROM entries WHERE done=1 AND completed_at >= datetime('now','-30 days')").fetchone()[0]
    total_pts   = conn.execute("SELECT COALESCE(SUM(points),0) FROM entries WHERE done=1").fetchone()[0]
    train_days  = conn.execute("SELECT COUNT(DISTINCT session_date) FROM cal_sessions").fetchone()[0]
    habit_30    = conn.execute("SELECT COUNT(*) FROM habit_logs WHERE log_date >= date('now','-30 days')").fetchone()[0]
    avg_sleep_q = conn.execute("SELECT AVG(quality_pct) FROM sleep_logs WHERE log_date >= date('now','-30 days')").fetchone()[0]
    cur_streak  = get_cal_streak()['current']
    conn.close()

    rate = done / total * 100 if total else 0
    hours_total = round(total_secs / 3600, 1)

    # ── 8 KPI Cards ────────────────────────────────────────────────
    kpi = ("text-align:center;background:rgba(255,255,255,0.04);border-radius:14px;"
           "padding:14px 6px;border:1px solid rgba(255,255,255,0.08)")
    kpis = [
        (str(done),         "#00d4ff", "✅ Erledigt"),
        (f"{rate:.0f}%",    "#ffd700", "📈 Quote"),
        (f"{hours_total}h", "#ff9500", "⏱️ Fokuszeit"),
        (str(active_30),    "#2ecc71", "📅 Aktive Tage"),
        (str(train_days),   "#a29bfe", "🏋️ Trainingstage"),
        (f"{cur_streak}🔥", "#ff6b6b", "Streak"),
        (str(habit_30),     "#74b9ff", "✅ Habits (30d)"),
        (f"{avg_sleep_q:.0f}%" if avg_sleep_q else "—", "#dfe6e9", "😴 Ø Schlaf"),
    ]
    cols = st.columns(8)
    for col, (val, color, label) in zip(cols, kpis):
        col.markdown(
            f'<div style="{kpi}"><div style="font-size:24px;font-weight:900;color:{color}">{val}</div>'
            f'<div style="color:rgba(255,255,255,0.4);font-size:10px;margin-top:4px">{label}</div></div>',
            unsafe_allow_html=True
        )

    st.write("")

    # ── Tabs ──────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "🏠 Überblick", "⏰ Zeitanalyse", "⏱️ Intraday",
        "😴 Schlaf & Routinen", "✅ Habits", "🏋️ Training",
        "📁 Projekte", "🤖 KI Analyse"
    ])

    _DARK = dict(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
                 plot_bgcolor='rgba(5,8,15,0.5)',
                 font=dict(color='white'))
    _GRID = dict(gridcolor='rgba(255,255,255,0.06)')

    # ══════════════════════════════════════════════════════════════
    # TAB 1 — ÜBERBLICK
    # ══════════════════════════════════════════════════════════════
    with tab1:
        # 365-Tage GitHub-Heatmap
        st.subheader("📅 Aktivitäts-Jahresrückblick (365 Tage)")
        conn2 = sqlite3.connect(DB_PATH)
        rows_365 = conn2.execute("""
            SELECT DATE(completed_at) as d, COUNT(*) as n
            FROM entries WHERE done=1 AND completed_at IS NOT NULL
            AND completed_at >= datetime('now','-365 days')
            GROUP BY d
        """).fetchall()
        conn2.close()

        if rows_365:
            day_counts = {r[0]: r[1] for r in rows_365}
            today_d = date.today()
            # Build 52-week grid
            start_d = today_d - timedelta(days=364)
            # Align to Monday
            start_d = start_d - timedelta(days=start_d.weekday())
            grid = []  # grid[week][weekday] = count
            cur = start_d
            week_data, labels = [], []
            while cur <= today_d + timedelta(days=6):
                week = []
                for wd in range(7):
                    d = cur + timedelta(days=wd)
                    week.append(day_counts.get(d.isoformat(), 0) if d <= today_d else None)
                week_data.append(week)
                labels.append(cur.strftime('%d.%m'))
                cur += timedelta(weeks=1)

            z = list(map(list, zip(*week_data)))  # transpose: 7 rows × N weeks
            day_names = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']

            fig_hm = go.Figure(go.Heatmap(
                z=z, x=labels, y=day_names,
                colorscale=[[0, 'rgba(255,255,255,0.05)'], [0.01, '#0a3d2e'],
                            [0.3, '#1a7a4a'], [0.7, '#2ecc71'], [1.0, '#00ff88']],
                showscale=False, hoverongaps=False,
                hovertemplate='%{x} %{y}: %{z} Aufgaben<extra></extra>',
                xgap=2, ygap=2
            ))
            fig_hm.update_layout(
                **_DARK, height=180,
                margin=dict(t=10, b=10, l=40, r=10),
                xaxis=dict(showgrid=False, tickangle=0,
                           tickvals=[labels[i] for i in range(0, len(labels), 4)],
                           ticktext=[labels[i] for i in range(0, len(labels), 4)]),
                yaxis=dict(showgrid=False, autorange='reversed')
            )
            st.plotly_chart(fig_hm, use_container_width=True)
        else:
            st.info("Noch keine Daten")

        st.markdown("---")

        cl, cr = st.columns(2)

        with cl:
            # Täglicher Trend 30 Tage
            st.subheader("Täglicher Fortschritt (30 Tage)")
            conn3 = sqlite3.connect(DB_PATH)
            trend = conn3.execute("""
                SELECT DATE(completed_at) as d, COUNT(*), SUM(elapsed_seconds)
                FROM entries WHERE done=1 AND completed_at IS NOT NULL
                AND completed_at >= datetime('now','-30 days')
                GROUP BY d ORDER BY d
            """).fetchall()
            conn3.close()
            if trend:
                df_trend = pd.DataFrame(trend, columns=['Datum','Aufgaben','Sek'])
                df_trend['Min'] = (df_trend['Sek'] / 60).round(0)
                fig_t = go.Figure()
                fig_t.add_trace(go.Bar(x=df_trend['Datum'], y=df_trend['Aufgaben'],
                                        name='Aufgaben', marker_color='rgba(0,212,255,0.7)',
                                        hovertemplate='%{x}: %{y} Aufgaben<extra></extra>'))
                fig_t.add_trace(go.Scatter(x=df_trend['Datum'], y=df_trend['Min'],
                                            name='Minuten', line=dict(color='#ffd700', width=2),
                                            yaxis='y2', mode='lines+markers',
                                            hovertemplate='%{x}: %{y} Min<extra></extra>'))
                fig_t.update_layout(**_DARK, height=280,
                                     yaxis=dict(title='Aufgaben', **_GRID),
                                     yaxis2=dict(title='Min', overlaying='y', side='right', **_GRID),
                                     margin=dict(t=10,b=30,l=40,r=50), hovermode='x unified',
                                     legend=dict(orientation='h', y=1.05, x=0))
                st.plotly_chart(fig_t, use_container_width=True)
            else:
                st.info("Keine Daten")

        with cr:
            # Wochentag-Produktivität
            st.subheader("Produktivster Wochentag")
            conn4 = sqlite3.connect(DB_PATH)
            wd_rows = conn4.execute("""
                SELECT CAST(strftime('%w', completed_at) AS INTEGER) as wd,
                       COUNT(*), SUM(elapsed_seconds)
                FROM entries WHERE done=1 AND completed_at IS NOT NULL
                GROUP BY wd
            """).fetchall()
            conn4.close()
            if wd_rows:
                wd_map = {0:'So',1:'Mo',2:'Di',3:'Mi',4:'Do',5:'Fr',6:'Sa'}
                df_wd = pd.DataFrame(wd_rows, columns=['wd','n','secs'])
                df_wd['tag'] = df_wd['wd'].map(wd_map)
                df_wd['min'] = (df_wd['secs'] / 60).round(0)
                order = ['Mo','Di','Mi','Do','Fr','Sa','So']
                df_wd['tag'] = pd.Categorical(df_wd['tag'], categories=order, ordered=True)
                df_wd = df_wd.sort_values('tag')
                fig_wd = go.Figure(go.Bar(
                    x=df_wd['tag'], y=df_wd['n'],
                    marker=dict(color=df_wd['n'],
                                colorscale=[[0,'rgba(162,155,254,0.2)'],[1,'#a29bfe']],
                                showscale=False),
                    text=df_wd['n'], textposition='outside',
                    hovertemplate='%{x}: %{y} Aufgaben, %{customdata} Min<extra></extra>',
                    customdata=df_wd['min']
                ))
                fig_wd.update_layout(**_DARK, height=280, yaxis=dict(title='Aufgaben', **_GRID),
                                      margin=dict(t=10,b=30,l=40,r=10))
                st.plotly_chart(fig_wd, use_container_width=True)
            else:
                st.info("Keine Daten")

        st.markdown("---")

        c1, c2, c3 = st.columns(3)
        with c1:
            # Aufgaben nach Typ
            st.subheader("Aufgaben nach Typ")
            conn5 = sqlite3.connect(DB_PATH)
            type_rows = conn5.execute(
                "SELECT entry_type, COUNT(*) FROM entries WHERE done=1 GROUP BY entry_type"
            ).fetchall()
            conn5.close()
            if type_rows:
                df_tp = pd.DataFrame(type_rows, columns=['Typ','n'])
                fig_pie = px.pie(df_tp, values='n', names='Typ', hole=0.45,
                                  color_discrete_sequence=['#00d4ff','#ff6b6b','#ffd93d','#a29bfe'])
                fig_pie.update_traces(textfont_size=12, textinfo='label+percent')
                fig_pie.update_layout(**_DARK, margin=dict(t=10,b=10,l=10,r=10), height=260)
                st.plotly_chart(fig_pie, use_container_width=True)

        with c2:
            # Fokuszeit nach Typ
            st.subheader("Ø Fokuszeit / Typ")
            conn6 = sqlite3.connect(DB_PATH)
            ft_rows = conn6.execute("""
                SELECT entry_type, AVG(elapsed_seconds), SUM(elapsed_seconds)
                FROM entries WHERE done=1 AND elapsed_seconds > 0 GROUP BY entry_type
            """).fetchall()
            conn6.close()
            if ft_rows:
                df_ft = pd.DataFrame(ft_rows, columns=['Typ','avg_s','tot_s'])
                df_ft['avg_min'] = (df_ft['avg_s'] / 60).round(1)
                fig_ft = go.Figure(go.Bar(
                    x=df_ft['Typ'], y=df_ft['avg_min'],
                    marker=dict(color=['#00d4ff','#ff6b6b','#ffd93d','#a29bfe'][:len(df_ft)]),
                    text=df_ft['avg_min'].apply(lambda x: f'{x:.0f}m'),
                    textposition='outside'
                ))
                fig_ft.update_layout(**_DARK, height=260, yaxis=dict(title='Minuten', **_GRID),
                                      margin=dict(t=10,b=30,l=40,r=10), showlegend=False)
                st.plotly_chart(fig_ft, use_container_width=True)

        with c3:
            # Persönliche Rekorde
            st.subheader("🏆 Rekorde")
            conn7 = sqlite3.connect(DB_PATH)
            best_day = conn7.execute("""
                SELECT DATE(completed_at), COUNT(*) FROM entries WHERE done=1 AND completed_at IS NOT NULL
                GROUP BY DATE(completed_at) ORDER BY COUNT(*) DESC LIMIT 1
            """).fetchone()
            best_min = conn7.execute("""
                SELECT DATE(completed_at), SUM(elapsed_seconds) FROM entries WHERE done=1 AND completed_at IS NOT NULL
                GROUP BY DATE(completed_at) ORDER BY SUM(elapsed_seconds) DESC LIMIT 1
            """).fetchone()
            longest = conn7.execute("""
                SELECT content, elapsed_seconds FROM entries WHERE done=1 AND elapsed_seconds > 0
                ORDER BY elapsed_seconds DESC LIMIT 1
            """).fetchone()
            consec = conn7.execute("""
                SELECT COUNT(DISTINCT entry_date) FROM entries WHERE done=1 AND entry_date >= date('now','-7 days')
            """).fetchone()[0]
            conn7.close()
            rs = "background:rgba(255,255,255,0.04);border-radius:10px;padding:9px 14px;margin-bottom:7px;border:1px solid rgba(255,255,255,0.08);font-size:12px"
            if best_day:
                st.markdown(f'<div style="{rs}">🥇 <strong>Bester Tag:</strong> {best_day[0]} ({best_day[1]} Aufg.)</div>', unsafe_allow_html=True)
            if best_min:
                st.markdown(f'<div style="{rs}">⏱️ <strong>Meiste Fokuszeit:</strong> {best_min[0]} ({round(best_min[1]/60)} Min)</div>', unsafe_allow_html=True)
            if longest:
                nm = longest[0][:35] + '…' if len(longest[0]) > 35 else longest[0]
                st.markdown(f'<div style="{rs}">🔥 <strong>Längste Session:</strong> {round(longest[1]/60)} Min<br><small style="color:rgba(255,255,255,0.4)">{nm}</small></div>', unsafe_allow_html=True)
            st.markdown(f'<div style="{rs}">📅 <strong>Aktive Tage (7d):</strong> {consec}/7</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="{rs}">🎯 <strong>Gesamt Fokuszeit:</strong> {round(total_secs/3600,1)} h</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="{rs}">🏅 <strong>Gesamt XP:</strong> {total_pts} Punkte</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    # TAB 2 — ZEITANALYSE
    # ══════════════════════════════════════════════════════════════
    with tab2:
        st.subheader("🕐 Produktivität nach Tagesstunde")
        conn_h = sqlite3.connect(DB_PATH)
        hour_rows = conn_h.execute("""
            SELECT CAST(strftime('%H', completed_at) AS INTEGER) as h,
                   COUNT(*), ROUND(SUM(elapsed_seconds)/60.0, 0)
            FROM entries WHERE done=1 AND completed_at IS NOT NULL
            GROUP BY h ORDER BY h
        """).fetchall()
        conn_h.close()
        if hour_rows:
            df_hr = pd.DataFrame(hour_rows, columns=['Stunde','Aufgaben','Minuten'])
            all_hours = pd.DataFrame({'Stunde': range(24)})
            df_hr = all_hours.merge(df_hr, on='Stunde', how='left').fillna(0)
            peak_h = int(df_hr.loc[df_hr['Aufgaben'].idxmax(), 'Stunde'])
            st.caption(f"Deine produktivste Stunde: **{peak_h}:00–{peak_h+1}:00 Uhr**")
            colors = ['#ffd700' if h == peak_h else '#00d4ff' for h in df_hr['Stunde']]
            fig_hr = go.Figure(go.Bar(
                x=[f"{h}h" for h in df_hr['Stunde']], y=df_hr['Aufgaben'],
                marker_color=colors, text=df_hr['Aufgaben'].astype(int),
                textposition='outside',
                hovertemplate='%{x}: %{y} Aufgaben, %{customdata} Min<extra></extra>',
                customdata=df_hr['Minuten'].astype(int)
            ))
            fig_hr.update_layout(**_DARK, height=280, yaxis=dict(title='Aufgaben', **_GRID),
                                  margin=dict(t=10,b=30,l=40,r=10))
            st.plotly_chart(fig_hr, use_container_width=True)
        else:
            st.info("Noch keine Zeitdaten")

        st.markdown("---")
        cl2, cr2 = st.columns(2)

        with cl2:
            st.subheader("📅 Wochentag × Stunde Heatmap")
            conn_wh = sqlite3.connect(DB_PATH)
            wh_rows = conn_wh.execute("""
                SELECT CAST(strftime('%w', completed_at) AS INTEGER) as wd,
                       CAST(strftime('%H', completed_at) AS INTEGER) as h,
                       COUNT(*)
                FROM entries WHERE done=1 AND completed_at IS NOT NULL
                GROUP BY wd, h
            """).fetchall()
            conn_wh.close()
            if wh_rows:
                import numpy as np
                wd_names = ['So','Mo','Di','Mi','Do','Fr','Sa']
                z_mat = [[0]*24 for _ in range(7)]
                for wd, h, n in wh_rows:
                    z_mat[wd][h] = n
                # Reorder Mo-So
                order_idx = [1,2,3,4,5,6,0]
                z_ordered = [z_mat[i] for i in order_idx]
                day_order = [wd_names[i] for i in order_idx]
                fig_wh = go.Figure(go.Heatmap(
                    z=z_ordered, x=[f"{h}h" for h in range(24)], y=day_order,
                    colorscale=[[0,'rgba(0,212,255,0.03)'],[0.3,'rgba(0,212,255,0.3)'],
                                [0.7,'#00d4ff'],[1,'#00ff88']],
                    showscale=True,
                    hovertemplate='%{y} %{x}: %{z} Aufgaben<extra></extra>',
                    xgap=1, ygap=1
                ))
                fig_wh.update_layout(**_DARK, height=260,
                                      margin=dict(t=10,b=30,l=40,r=10),
                                      xaxis=dict(showgrid=False),
                                      yaxis=dict(showgrid=False, autorange='reversed'))
                st.plotly_chart(fig_wh, use_container_width=True)
            else:
                st.info("Noch keine Daten")

        with cr2:
            st.subheader("🎯 Schätzgenauigkeit")
            conn_est = sqlite3.connect(DB_PATH)
            est_rows = conn_est.execute("""
                SELECT estimate_minutes, elapsed_seconds / 60.0 as actual_min, entry_type
                FROM entries WHERE done=1 AND estimate_minutes > 0 AND elapsed_seconds > 30
                ORDER BY completed_at DESC LIMIT 150
            """).fetchall()
            conn_est.close()
            if est_rows:
                df_est = pd.DataFrame(est_rows, columns=['Geschätzt','Actual','Typ'])
                # Overall accuracy
                df_est['Diff_pct'] = ((df_est['Actual'] - df_est['Geschätzt']) / df_est['Geschätzt'] * 100).round(0)
                over = (df_est['Diff_pct'] > 20).sum()
                under = (df_est['Diff_pct'] < -20).sum()
                exact = len(df_est) - over - under
                st.caption(f"Letzte 150 Aufgaben: **{exact}** genau, **{over}** unterschätzt, **{under}** überschätzt")
                max_val = max(df_est['Geschätzt'].max(), df_est['Actual'].max(), 1)
                fig_est = go.Figure()
                fig_est.add_trace(go.Scatter(x=[0, max_val], y=[0, max_val],
                                              mode='lines', line=dict(color='rgba(255,255,255,0.2)', dash='dash'),
                                              name='Perfekt', showlegend=True))
                colors_est = {'brain':'#00d4ff','highlight':'#ff6b6b','micro':'#ffd93d'}
                for typ in df_est['Typ'].unique():
                    df_sub = df_est[df_est['Typ']==typ]
                    fig_est.add_trace(go.Scatter(
                        x=df_sub['Geschätzt'], y=df_sub['Actual'],
                        mode='markers', name=typ,
                        marker=dict(color=colors_est.get(typ,'#a29bfe'), size=7, opacity=0.7),
                        hovertemplate='Geschätzt: %{x}m → Tatsächlich: %{y:.0f}m<extra></extra>'
                    ))
                fig_est.update_layout(**_DARK, height=280, xaxis=dict(title='Geschätzt (Min)', **_GRID),
                                       yaxis=dict(title='Tatsächlich (Min)', **_GRID),
                                       margin=dict(t=10,b=40,l=50,r=10),
                                       legend=dict(orientation='h', y=1.05))
                st.plotly_chart(fig_est, use_container_width=True)
            else:
                st.info("Noch keine Schätzungen mit Zeiterfassung")

        st.markdown("---")
        st.subheader("🏷️ Tag-Analyse")
        conn_tag = sqlite3.connect(DB_PATH)
        tag_rows = conn_tag.execute("""
            SELECT tags, COUNT(*) as n, ROUND(AVG(elapsed_seconds)/60.0,0) as avg_min,
                   ROUND(SUM(elapsed_seconds)/3600.0,1) as total_h
            FROM entries WHERE done=1 AND tags IS NOT NULL AND tags != ''
            GROUP BY tags ORDER BY n DESC LIMIT 20
        """).fetchall()
        conn_tag.close()
        if tag_rows:
            df_tag = pd.DataFrame(tag_rows, columns=['Tag','Aufgaben','Ø Min','Gesamt h'])
            df_tag = df_tag[~df_tag['Tag'].str.contains('projekt', case=False, na=False)]
            fig_tag = go.Figure(go.Bar(
                x=df_tag['Tag'], y=df_tag['Aufgaben'],
                marker=dict(color=df_tag['Aufgaben'],
                            colorscale=[[0,'rgba(162,155,254,0.2)'],[1,'#a29bfe']],
                            showscale=False),
                text=df_tag['Aufgaben'], textposition='outside',
                hovertemplate='%{x}: %{y} Aufg. | Ø %{customdata[0]} Min | %{customdata[1]}h gesamt<extra></extra>',
                customdata=df_tag[['Ø Min','Gesamt h']].values
            ))
            fig_tag.update_layout(**_DARK, height=260, yaxis=dict(title='Aufgaben', **_GRID),
                                   margin=dict(t=10,b=40,l=40,r=10))
            st.plotly_chart(fig_tag, use_container_width=True)
        else:
            st.info("Noch keine Tag-Daten")

    # ══════════════════════════════════════════════════════════════
    # TAB 3 — SCHLAF & ROUTINEN
    # ══════════════════════════════════════════════════════════════
    with tab3:
        conn_sl = sqlite3.connect(DB_PATH)
        sleep_rows = conn_sl.execute("""
            SELECT log_date, quality_pct, bedtime, wake_time
            FROM sleep_logs WHERE log_date >= date('now','-60 days') ORDER BY log_date
        """).fetchall()
        routine_rows = conn_sl.execute("""
            SELECT log_date, routine, SUM(done) as done_sum, COUNT(*) as total_tasks
            FROM routine_checks WHERE log_date >= date('now','-60 days')
            GROUP BY log_date, routine ORDER BY log_date
        """).fetchall()
        # Schlaf vs nächster Tag Produktivität
        prod_rows = conn_sl.execute("""
            SELECT entry_date, ROUND(AVG(done)*100,0) as rate, COUNT(*) as n
            FROM entries WHERE entry_date >= date('now','-60 days')
            GROUP BY entry_date
        """).fetchall()
        conn_sl.close()

        if sleep_rows:
            df_sl = pd.DataFrame(sleep_rows, columns=['Datum','Qualität_pct','Bettzeit','Aufstehen'])
            df_sl['Qualität'] = (df_sl['Qualität_pct'] / 20).round(1)  # 0-5 Skala

            cl3, cr3 = st.columns(2)
            with cl3:
                st.subheader("😴 Schlafqualität (60 Tage)")
                fig_sl = go.Figure()
                fig_sl.add_trace(go.Bar(
                    x=df_sl['Datum'], y=df_sl['Qualität'],
                    marker=dict(color=df_sl['Qualität_pct'],
                                colorscale=[[0,'#e74c3c'],[0.5,'#f39c12'],[1,'#2ecc71']],
                                showscale=False),
                    hovertemplate='%{x}: %{y:.1f}/5<extra></extra>'
                ))
                fig_sl.add_hline(y=df_sl['Qualität'].mean(), line_dash='dash',
                                  line_color='rgba(255,255,255,0.4)',
                                  annotation_text=f"Ø {df_sl['Qualität'].mean():.1f}",
                                  annotation_font_color='rgba(255,255,255,0.6)')
                fig_sl.update_layout(**_DARK, height=250, yaxis=dict(title='Qualität (0-5)', range=[0,5.5], **_GRID),
                                      margin=dict(t=10,b=30,l=40,r=10))
                st.plotly_chart(fig_sl, use_container_width=True)

            with cr3:
                # Schlaf-Qualität vs Produktivität nächster Tag
                st.subheader("🔗 Schlaf → Produktivität")
                if prod_rows:
                    df_prod = pd.DataFrame(prod_rows, columns=['Datum','Rate','n'])
                    # Join: sleep day → next day's productivity
                    df_sl_copy = df_sl.copy()
                    df_sl_copy['NextDay'] = pd.to_datetime(df_sl_copy['Datum']) + pd.Timedelta(days=1)
                    df_sl_copy['NextDay'] = df_sl_copy['NextDay'].dt.strftime('%Y-%m-%d')
                    merged = df_sl_copy.merge(df_prod, left_on='NextDay', right_on='Datum', how='inner')
                    if len(merged) >= 3:
                        fig_corr = go.Figure(go.Scatter(
                            x=merged['Qualität_pct'], y=merged['Rate'],
                            mode='markers', marker=dict(color='#74b9ff', size=10, opacity=0.8),
                            hovertemplate='Schlaf: %{x}% → nächster Tag: %{y:.0f}%<extra></extra>'
                        ))
                        # Trendlinie
                        try:
                            import numpy as np
                            z = np.polyfit(merged['Qualität_pct'], merged['Rate'], 1)
                            p = np.poly1d(z)
                            x_line = [merged['Qualität_pct'].min(), merged['Qualität_pct'].max()]
                            fig_corr.add_trace(go.Scatter(x=x_line, y=[p(x) for x in x_line],
                                                           mode='lines', line=dict(color='#ffd700', dash='dash'),
                                                           name='Trend'))
                        except Exception:
                            pass
                        fig_corr.update_layout(**_DARK, height=250,
                                               xaxis=dict(title='Schlafqualität (%)', **_GRID),
                                               yaxis=dict(title='Erledigungsquote nächster Tag (%)', **_GRID),
                                               margin=dict(t=10,b=40,l=50,r=10), showlegend=False)
                        st.plotly_chart(fig_corr, use_container_width=True)
                    else:
                        st.info("Noch nicht genug Daten für Korrelation (mind. 3 Nächte)")
                else:
                    st.info("Keine Produktivitätsdaten")
        else:
            st.info("Noch keine Schlafdaten — logge deinen Schlaf auf der Schlaf-Seite.")

        st.markdown("---")

        if routine_rows:
            st.subheader("🌅 Routinen-Adhärenz")
            df_rt = pd.DataFrame(routine_rows, columns=['Datum','Routine','Erledigt','Total'])
            df_rt['Pct'] = (df_rt['Erledigt'] / df_rt['Total'] * 100).round(0)
            df_morning = df_rt[df_rt['Routine']=='morning']
            df_evening = df_rt[df_rt['Routine']=='evening']

            fig_rt = go.Figure()
            if not df_morning.empty:
                fig_rt.add_trace(go.Scatter(x=df_morning['Datum'], y=df_morning['Pct'],
                                             mode='lines+markers', name='🌅 Morgen',
                                             line=dict(color='#f39c12', width=2),
                                             fill='tozeroy', fillcolor='rgba(243,156,18,0.08)'))
            if not df_evening.empty:
                fig_rt.add_trace(go.Scatter(x=df_evening['Datum'], y=df_evening['Pct'],
                                             mode='lines+markers', name='🌙 Abend',
                                             line=dict(color='#a29bfe', width=2),
                                             fill='tozeroy', fillcolor='rgba(162,155,254,0.06)'))
            fig_rt.add_hline(y=100, line_dash='dot', line_color='rgba(46,204,113,0.4)',
                              annotation_text='100% ✓', annotation_font_color='#2ecc71')
            fig_rt.update_layout(**_DARK, height=260, yaxis=dict(title='Adhärenz %', range=[0,110], **_GRID),
                                  margin=dict(t=10,b=30,l=40,r=10),
                                  legend=dict(orientation='h', y=1.05), hovermode='x unified')
            st.plotly_chart(fig_rt, use_container_width=True)
        else:
            st.info("Noch keine Routinen-Daten")

    # ══════════════════════════════════════════════════════════════
    # TAB 4 — HABITS
    # ══════════════════════════════════════════════════════════════
    with tab4:
        conn_hab = sqlite3.connect(DB_PATH)
        habits_list = conn_hab.execute("SELECT id, name, icon, color FROM habits").fetchall()
        if habits_list:
            st.subheader("✅ Habit-Kalender (letzte 30 Tage)")
            today_d = date.today()
            last_30 = [(today_d - timedelta(days=i)).isoformat() for i in range(29, -1, -1)]
            # Build heatmap
            z_hab = []
            y_hab = []
            for hid, hname, hicon, hcolor in habits_list:
                logs = conn_hab.execute(
                    "SELECT log_date FROM habit_logs WHERE habit_id=? AND log_date >= date('now','-30 days')",
                    (hid,)
                ).fetchall()
                log_set = {r[0] for r in logs}
                row = [1 if d in log_set else 0 for d in last_30]
                z_hab.append(row)
                streak = 0
                for d in reversed(last_30):
                    if d in log_set:
                        streak += 1
                    else:
                        break
                total_30 = sum(row)
                y_hab.append(f"{hicon} {hname} ({total_30}/30, {streak}🔥)")

            fig_hab = go.Figure(go.Heatmap(
                z=z_hab, x=[d[5:] for d in last_30], y=y_hab,  # mm-dd
                colorscale=[[0,'rgba(255,255,255,0.04)'],[1,'#2ecc71']],
                showscale=False,
                hovertemplate='%{y}<br>%{x}: %{z}<extra></extra>',
                xgap=2, ygap=3
            ))
            fig_hab.update_layout(
                **_DARK, height=max(180, len(habits_list) * 45 + 60),
                margin=dict(t=10,b=30,l=180,r=10),
                xaxis=dict(showgrid=False, tickangle=45,
                           tickvals=[last_30[i][5:] for i in range(0, 30, 5)],
                           ticktext=[last_30[i][5:] for i in range(0, 30, 5)]),
                yaxis=dict(showgrid=False, autorange='reversed')
            )
            st.plotly_chart(fig_hab, use_container_width=True)

            st.markdown("---")
            st.subheader("📊 Habit-Konsistenz (30 Tage)")
            hab_stats = []
            for hid, hname, hicon, hcolor in habits_list:
                count = conn_hab.execute(
                    "SELECT COUNT(*) FROM habit_logs WHERE habit_id=? AND log_date >= date('now','-30 days')",
                    (hid,)
                ).fetchone()[0]
                hab_stats.append((f"{hicon} {hname}", count, round(count/30*100)))
            conn_hab.close()
            df_hcon = pd.DataFrame(hab_stats, columns=['Habit','Tage','Pct']).sort_values('Tage', ascending=True)
            fig_hcon = go.Figure(go.Bar(
                x=df_hcon['Tage'], y=df_hcon['Habit'], orientation='h',
                marker=dict(color=df_hcon['Pct'],
                            colorscale=[[0,'#e74c3c'],[0.5,'#f39c12'],[1,'#2ecc71']],
                            showscale=False),
                text=[f"{p}%" for p in df_hcon['Pct']], textposition='outside',
                hovertemplate='%{y}: %{x}/30 Tage (%{text})<extra></extra>'
            ))
            fig_hcon.update_layout(**_DARK, height=max(180, len(habits_list)*50 + 60),
                                    xaxis=dict(title='Tage (von 30)', **_GRID),
                                    margin=dict(t=10,b=30,l=180,r=60))
            st.plotly_chart(fig_hcon, use_container_width=True)
        else:
            conn_hab.close()
            st.info("Noch keine Habits konfiguriert — lege Habits auf der Habits-Seite an.")

    # ══════════════════════════════════════════════════════════════
    # TAB 5 — TRAINING
    # ══════════════════════════════════════════════════════════════
    with tab5:
        conn_tr = sqlite3.connect(DB_PATH)
        session_rows = conn_tr.execute("""
            SELECT session_date, track, COUNT(*) as sets, SUM(clean) as clean_sets,
                   AVG(best_reps) as avg_reps
            FROM cal_sessions GROUP BY session_date, track ORDER BY session_date
        """).fetchall()
        track_summary = conn_tr.execute("""
            SELECT track, COUNT(DISTINCT session_date) as days,
                   SUM(sets_completed) as total_sets, AVG(clean) as clean_rate,
                   MAX(best_reps) as max_reps
            FROM cal_sessions GROUP BY track
        """).fetchall()
        weekly_vol = conn_tr.execute("""
            SELECT strftime('%Y-W%W', session_date) as week, COUNT(DISTINCT session_date) as days,
                   COUNT(*) as total_sets
            FROM cal_sessions WHERE session_date >= date('now','-90 days')
            GROUP BY week ORDER BY week
        """).fetchall()
        conn_tr.close()

        if not session_rows:
            st.info("Noch keine Trainingsdaten — starte dein erstes Training!")
        else:
            streak_data = get_cal_streak()

            # KPIs
            tr_k1, tr_k2, tr_k3, tr_k4 = st.columns(4)
            tr_k1.metric("Trainingstage gesamt", streak_data['total_sessions'])
            tr_k2.metric("Aktueller Streak", f"{streak_data['current']} 🔥")
            tr_k3.metric("Rekord-Streak", f"{streak_data['longest']} 🏆")
            total_clean = sum(r[3] or 0 for r in session_rows)
            total_sets_all = sum(r[2] or 0 for r in session_rows)
            overall_clean = round(total_clean / total_sets_all * 100) if total_sets_all else 0
            tr_k4.metric("Clean Rate gesamt", f"{overall_clean}%")

            st.markdown("---")

            cl5, cr5 = st.columns(2)
            with cl5:
                # Sessions pro Track
                st.subheader("🏋️ Sessions pro Track")
                if track_summary:
                    df_trs = pd.DataFrame(track_summary, columns=['Track','Tage','Sets','CleanRate','MaxReps'])
                    df_trs['Track_label'] = df_trs['Track'].apply(lambda t: CAL_TRACKS.get(t, {}).get('label', t))
                    df_trs['CleanPct'] = (df_trs['CleanRate'] * 100).round(0)
                    df_trs['Color'] = df_trs['Track'].apply(lambda t: CAL_TRACKS.get(t, {}).get('color', '#aaa'))
                    fig_trs = go.Figure(go.Bar(
                        x=df_trs['Track_label'], y=df_trs['Tage'],
                        marker_color=df_trs['Color'].tolist(),
                        text=df_trs['Tage'], textposition='outside',
                        hovertemplate='%{x}: %{y} Tage | Clean: %{customdata}%<extra></extra>',
                        customdata=df_trs['CleanPct']
                    ))
                    fig_trs.update_layout(**_DARK, height=260, yaxis=dict(title='Trainingstage', **_GRID),
                                           margin=dict(t=10,b=40,l=40,r=10), showlegend=False)
                    st.plotly_chart(fig_trs, use_container_width=True)

            with cr5:
                # Clean Rate pro Track
                st.subheader("✅ Clean Rate pro Track")
                if track_summary:
                    df_cr = pd.DataFrame(track_summary, columns=['Track','Tage','Sets','CleanRate','MaxReps'])
                    df_cr = df_cr[df_cr['Tage'] > 0]
                    df_cr['Track_label'] = df_cr['Track'].apply(lambda t: CAL_TRACKS.get(t, {}).get('label', t))
                    df_cr['CleanPct'] = (df_cr['CleanRate'] * 100).round(0)
                    df_cr['Color'] = df_cr['Track'].apply(lambda t: CAL_TRACKS.get(t, {}).get('color', '#aaa'))
                    df_cr = df_cr.sort_values('CleanPct', ascending=True)
                    fig_cr = go.Figure(go.Bar(
                        x=df_cr['CleanPct'], y=df_cr['Track_label'], orientation='h',
                        marker_color=df_cr['Color'].tolist(),
                        text=[f"{p:.0f}%" for p in df_cr['CleanPct']], textposition='outside',
                        hovertemplate='%{y}: %{x:.0f}% clean<extra></extra>'
                    ))
                    fig_cr.update_layout(**_DARK, height=260, xaxis=dict(title='Clean %', range=[0,115], **_GRID),
                                          margin=dict(t=10,b=30,l=100,r=60))
                    st.plotly_chart(fig_cr, use_container_width=True)

            st.markdown("---")
            st.subheader("📈 Wöchentliches Trainingsvolumen (90 Tage)")
            if weekly_vol:
                df_wv = pd.DataFrame(weekly_vol, columns=['Woche','Tage','Sets'])
                fig_wv = go.Figure()
                fig_wv.add_trace(go.Bar(x=df_wv['Woche'], y=df_wv['Tage'],
                                         name='Trainingstage', marker_color='rgba(0,212,255,0.6)'))
                fig_wv.add_trace(go.Scatter(x=df_wv['Woche'], y=df_wv['Sets'],
                                             name='Sätze', yaxis='y2',
                                             line=dict(color='#ffd700', width=2),
                                             mode='lines+markers'))
                fig_wv.update_layout(**_DARK, height=260, yaxis=dict(title='Tage', **_GRID),
                                      yaxis2=dict(title='Sätze', overlaying='y', side='right', **_GRID),
                                      margin=dict(t=10,b=30,l=40,r=50),
                                      legend=dict(orientation='h', y=1.05), hovermode='x unified')
                st.plotly_chart(fig_wv, use_container_width=True)

            # Level-Fortschritt pro Track
            st.markdown("---")
            st.subheader("🎯 Aktueller Level-Stand")
            prog_all = get_cal_progress()
            track_cols = st.columns(3)
            for i, (track, info) in enumerate(CAL_TRACKS.items()):
                p = prog_all[track]
                ex = get_cal_exercise(track, p['level'], p['bonus'])
                pct = (p['level'] / max(len(info['levels']) - 1, 1)) * 100
                with track_cols[i % 3]:
                    st.markdown(
                        f'<div style="background:rgba(255,255,255,0.03);border:1px solid {info["color"]}33;'
                        f'border-radius:12px;padding:12px 14px;margin-bottom:10px">'
                        f'<div style="font-size:13px;font-weight:700;color:white;margin-bottom:6px">'
                        f'{info["icon"]} {info["label"]}</div>'
                        f'<div style="font-size:11px;color:{info["color"]};margin-bottom:4px">'
                        f'Level {p["level"]+1}/{len(info["levels"])} · {ex["name"]}</div>'
                        f'<div style="height:4px;background:rgba(255,255,255,0.07);border-radius:2px">'
                        f'<div style="width:{min(pct,100):.0f}%;height:100%;background:{info["color"]};border-radius:2px"></div>'
                        f'</div></div>',
                        unsafe_allow_html=True
                    )

    # ══════════════════════════════════════════════════════════════
    # TAB 6 — PROJEKTE
    # ══════════════════════════════════════════════════════════════
    with tab6:
        conn_pr = sqlite3.connect(DB_PATH)
        projects_all = conn_pr.execute("""
            SELECT id, name, deadline, color, daily_minutes, COALESCE(roter_faden,'')
            FROM projects WHERE active=1
        """).fetchall()

        if not projects_all:
            conn_pr.close()
            st.info("Noch keine aktiven Projekte — erstelle Projekte auf der Projekte-Seite.")
        else:
            # Gesamt-Übersicht
            all_tasks = conn_pr.execute("SELECT project_id, done, estimate_minutes FROM project_tasks").fetchall()
            conn_pr.close()

            total_proj_tasks = len(all_tasks)
            done_proj_tasks  = sum(1 for t in all_tasks if t[1])
            proj_rate = done_proj_tasks / total_proj_tasks * 100 if total_proj_tasks else 0

            pk1, pk2, pk3 = st.columns(3)
            pk1.metric("Aktive Projekte", len(projects_all))
            pk2.metric("Tasks erledigt", f"{done_proj_tasks}/{total_proj_tasks}")
            pk3.metric("Erledigungsrate", f"{proj_rate:.0f}%")

            st.markdown("---")
            st.subheader("📊 Projektfortschritt")

            task_by_proj = {}
            for task in all_tasks:
                pid = task[0]
                task_by_proj.setdefault(pid, []).append(task)

            for proj_id, name, deadline, color, daily_mins, roter_faden in projects_all:
                tasks = task_by_proj.get(proj_id, [])
                t_total = len(tasks)
                t_done  = sum(1 for t in tasks if t[1])
                t_pct   = t_done / t_total * 100 if t_total else 0
                t_rem_min = sum(t[2] or 0 for t in tasks if not t[1])

                try:
                    dl_d = date.fromisoformat(deadline)
                    days_left = (dl_d - date.today()).days
                    dl_str = f"📅 noch {days_left}d"
                    dl_color = '#e74c3c' if days_left <= 7 else ('#f39c12' if days_left <= 21 else '#2ecc71')
                except Exception:
                    dl_str = ''
                    dl_color = 'rgba(255,255,255,0.4)'

                bar_w = int(t_pct)
                st.markdown(
                    f'<div style="border-left:3px solid {color};border-radius:0 10px 10px 0;'
                    f'background:rgba(255,255,255,0.02);padding:12px 16px;margin-bottom:4px">'
                    f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">'
                    f'<strong style="font-size:14px;color:white">{name}</strong>'
                    f'<span style="font-size:11px;font-weight:700;color:{dl_color}">{dl_str}</span>'
                    f'<span style="font-size:11px;color:rgba(255,255,255,0.4);margin-left:auto">'
                    f'{t_done}/{t_total} · {t_pct:.0f}% · {t_rem_min} min offen</span>'
                    f'</div>'
                    + (f'<div style="font-size:11px;color:rgba(255,255,255,0.4);margin-top:3px;font-style:italic">🧵 {roter_faden[:80]}</div>' if roter_faden else '')
                    + f'<div style="height:6px;background:rgba(255,255,255,0.06);border-radius:3px;margin-top:8px">'
                    f'<div style="width:{bar_w}%;height:100%;background:{color};border-radius:3px"></div>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )

            st.markdown("---")
            # Projekt-Tasks nach Status (Donut)
            col_pA, col_pB = st.columns(2)
            with col_pA:
                st.subheader("Tasks-Übersicht")
                done_min = sum(t[2] or 0 for t in all_tasks if t[1])
                open_min = sum(t[2] or 0 for t in all_tasks if not t[1])
                fig_pd = go.Figure(go.Pie(
                    labels=['Erledigt', 'Offen'],
                    values=[done_proj_tasks, total_proj_tasks - done_proj_tasks],
                    hole=0.5,
                    marker_colors=['#2ecc71', 'rgba(255,255,255,0.1)'],
                    textfont_size=13
                ))
                fig_pd.update_layout(**_DARK, height=220, margin=dict(t=10,b=10,l=10,r=10))
                st.plotly_chart(fig_pd, use_container_width=True)
                st.caption(f"Offene Arbeit: {open_min} min · Erledigt: {done_min} min")

            with col_pB:
                st.subheader("Zeit offen pro Projekt")
                proj_open_mins = []
                for proj_id, name, deadline, color, daily_mins, _ in projects_all:
                    tasks = task_by_proj.get(proj_id, [])
                    rem = sum(t[2] or 0 for t in tasks if not t[1])
                    if rem > 0:
                        proj_open_mins.append((name[:20], rem, color))
                if proj_open_mins:
                    df_pom = pd.DataFrame(proj_open_mins, columns=['Projekt','Min','Color']).sort_values('Min')
                    fig_pom = go.Figure(go.Bar(
                        x=df_pom['Min'], y=df_pom['Projekt'], orientation='h',
                        marker_color=df_pom['Color'].tolist(),
                        text=[f"{m} min" for m in df_pom['Min']], textposition='outside'
                    ))
                    fig_pom.update_layout(**_DARK, height=220,
                                          xaxis=dict(title='Minuten offen', **_GRID),
                                          margin=dict(t=10,b=30,l=120,r=70))
                    st.plotly_chart(fig_pom, use_container_width=True)

    # ══════════════════════════════════════════════════════════════
    # TAB 7 — INTRADAY (Tiefen-Zeitanalyse)
    # ══════════════════════════════════════════════════════════════
    with tab7:
        conn_id = sqlite3.connect(DB_PATH)

        # Dot-Timeline: wann wurden Tasks erledigt (letzte 14 Tage)
        timeline_rows = conn_id.execute("""
            SELECT entry_date,
                   CAST(strftime('%H', started_at) AS INTEGER) as h,
                   CAST(strftime('%M', started_at) AS INTEGER) as m,
                   elapsed_seconds, entry_type, content
            FROM entries
            WHERE done=1 AND started_at IS NOT NULL
            AND entry_date >= date('now','-14 days')
            ORDER BY entry_date, started_at
        """).fetchall()

        # Tagesstart/ende pro Tag
        day_bounds = conn_id.execute("""
            SELECT entry_date,
                   strftime('%H:%M', MIN(started_at)) as first_start,
                   strftime('%H:%M', MAX(completed_at)) as last_done,
                   COUNT(*) as tasks,
                   SUM(elapsed_seconds) as total_secs
            FROM entries WHERE done=1 AND started_at IS NOT NULL AND completed_at IS NOT NULL
            AND entry_date >= date('now','-30 days')
            GROUP BY entry_date ORDER BY entry_date
        """).fetchall()

        # Ø Task-Dauer nach Stunde
        dur_by_hour = conn_id.execute("""
            SELECT CAST(strftime('%H', started_at) AS INTEGER) as h,
                   AVG(elapsed_seconds) as avg_secs, COUNT(*) as n
            FROM entries WHERE done=1 AND started_at IS NOT NULL AND elapsed_seconds > 0
            GROUP BY h ORDER BY h
        """).fetchall()

        # Focus-Block Daten
        focus_rows = conn_id.execute("""
            SELECT started_at, completed_at, elapsed_seconds, entry_type
            FROM entries WHERE done=1 AND started_at IS NOT NULL AND completed_at IS NOT NULL
            AND started_at >= datetime('now','-30 days')
            ORDER BY started_at
        """).fetchall()

        # Session-Längen
        dur_rows = conn_id.execute("""
            SELECT elapsed_seconds, entry_type
            FROM entries WHERE done=1 AND elapsed_seconds > 30
            ORDER BY completed_at DESC LIMIT 500
        """).fetchall()

        # Produktivitätsverlauf nach 2h-Blöcken (Intraday-Kurve)
        intraday_curve = conn_id.execute("""
            SELECT CAST(strftime('%H', completed_at) AS INTEGER) / 2 * 2 as block_start,
                   COUNT(*) as n, SUM(elapsed_seconds) as secs
            FROM entries WHERE done=1 AND completed_at IS NOT NULL
            GROUP BY block_start ORDER BY block_start
        """).fetchall()

        # Context-Switch-Analyse
        switches = conn_id.execute("""
            SELECT entry_date,
                   entry_type,
                   LAG(entry_type) OVER (PARTITION BY entry_date ORDER BY started_at) as prev_type
            FROM entries
            WHERE done=1 AND started_at IS NOT NULL
            AND entry_date >= date('now','-30 days')
        """).fetchall()

        conn_id.close()

        # ── Dot-Timeline ──────────────────────────────────────────
        st.subheader("📍 Aufgaben-Dot-Timeline (letzte 14 Tage)")
        if timeline_rows:
            type_colors = {'brain':'#00d4ff','highlight':'#ffd700','micro':'#ff6b6b','projekt':'#a29bfe'}
            dates_seen = []
            fig_tl = go.Figure()
            by_type = {}
            for row in timeline_rows:
                d, h, m, secs, etype, content = row
                if h is None or m is None:
                    continue
                x_val = h + (m or 0) / 60
                size = max(7, min(28, (secs or 300) / 60))
                color = type_colors.get(etype, '#dfe6e9')
                short = (content or '')[:45] + '…' if len(content or '') > 45 else (content or '')
                by_type.setdefault(etype, {'x':[],'y':[],'size':[],'text':[],'color':color})
                by_type[etype]['x'].append(x_val)
                by_type[etype]['y'].append(d)
                by_type[etype]['size'].append(size)
                by_type[etype]['text'].append(f"{d} {h:02d}:{(m or 0):02d} — {short}<br>{round((secs or 0)/60)} Min")

            for etype, data in by_type.items():
                fig_tl.add_trace(go.Scatter(
                    x=data['x'], y=data['y'], mode='markers',
                    marker=dict(size=data['size'], color=data['color'], opacity=0.8,
                                line=dict(color='rgba(255,255,255,0.15)', width=1)),
                    name=etype, text=data['text'], hoverinfo='text'
                ))

            fig_tl.update_layout(
                **_DARK, height=380,
                xaxis=dict(title='Uhrzeit', range=[-0.5, 23.5],
                           tickvals=list(range(0, 24, 2)),
                           ticktext=[f"{h}:00" for h in range(0, 24, 2)], **_GRID),
                yaxis=dict(autorange='reversed', **_GRID),
                margin=dict(t=10,b=40,l=80,r=10),
                legend=dict(orientation='h', y=1.05), hovermode='closest'
            )
            st.caption("Punktgröße = Dauer · Farbe = Typ (Brain=blau, Highlight=gelb, Micro=rot)")
            st.plotly_chart(fig_tl, use_container_width=True)
        else:
            st.info("Noch keine Zeitdaten — aktiviere den Timer beim Bearbeiten von Aufgaben.")

        st.markdown("---")

        # ── Intraday-Produktivitätskurve ──────────────────────────
        st.subheader("⚡ Intraday-Energie-Kurve (2h-Blöcke)")
        if intraday_curve:
            df_ic = pd.DataFrame(intraday_curve, columns=['start_h','n','secs'])
            df_ic['label'] = df_ic['start_h'].apply(lambda h: f"{h:02d}–{h+2:02d}h")
            df_ic['min'] = (df_ic['secs'] / 60).round(0)
            peak_block = df_ic.loc[df_ic['n'].idxmax()]
            fig_ic = go.Figure()
            fig_ic.add_trace(go.Bar(
                x=df_ic['label'], y=df_ic['n'],
                marker=dict(
                    color=df_ic['n'],
                    colorscale=[[0,'rgba(0,212,255,0.1)'],[0.5,'rgba(0,212,255,0.5)'],[1,'#00ff88']],
                    showscale=False
                ),
                text=df_ic['n'], textposition='outside', name='Aufgaben',
                hovertemplate='%{x}: %{y} Aufgaben, %{customdata} Min<extra></extra>',
                customdata=df_ic['min']
            ))
            fig_ic.add_trace(go.Scatter(
                x=df_ic['label'], y=df_ic['min'], mode='lines+markers',
                name='Fokuszeit (Min)', yaxis='y2',
                line=dict(color='#ffd700', width=2),
                marker=dict(size=6)
            ))
            fig_ic.update_layout(
                **_DARK, height=260, hovermode='x unified',
                xaxis=dict(**_GRID),
                yaxis=dict(title='Aufgaben', **_GRID),
                yaxis2=dict(title='Minuten', overlaying='y', side='right', **_GRID),
                margin=dict(t=10,b=40,l=40,r=50),
                legend=dict(orientation='h', y=1.05)
            )
            st.caption(f"Produktivster Block: **{peak_block['label']}** mit {int(peak_block['n'])} Aufgaben")
            st.plotly_chart(fig_ic, use_container_width=True)

        st.markdown("---")

        cl7a, cr7a = st.columns(2)

        with cl7a:
            # ── Tagesstart-Uhrzeit-Trend ──────────────────────────
            st.subheader("🌅 Tagesstart-Trend (30 Tage)")
            if day_bounds:
                def hhmm_dec(s):
                    if not s:
                        return None
                    try:
                        parts = s.split(':')
                        return int(parts[0]) + int(parts[1]) / 60
                    except Exception:
                        return None

                df_db = pd.DataFrame(day_bounds, columns=['Datum','Erster','Letzter','Tasks','Secs'])
                df_db['start_h'] = df_db['Erster'].apply(hhmm_dec)
                df_db['end_h']   = df_db['Letzter'].apply(hhmm_dec)
                df_db['dur_h']   = (df_db['Secs'] / 3600).round(1)
                df_db = df_db.dropna(subset=['start_h'])

                if not df_db.empty:
                    avg_s = df_db['start_h'].mean()
                    avg_e = df_db['end_h'].dropna().mean()

                    fig_db = go.Figure()
                    fig_db.add_trace(go.Scatter(
                        x=df_db['Datum'], y=df_db['start_h'], mode='markers+lines',
                        name='🌅 Tagesstart', marker=dict(color='#ffd700', size=8),
                        line=dict(color='rgba(255,215,0,0.4)', width=1),
                        text=df_db['Erster'], hovertemplate='%{x}: %{text}<extra></extra>'
                    ))
                    fig_db.add_trace(go.Scatter(
                        x=df_db['Datum'], y=df_db['end_h'].fillna(method='ffill'),
                        mode='markers+lines', name='🌙 Tagesende',
                        marker=dict(color='#a29bfe', size=6),
                        line=dict(color='rgba(162,155,254,0.3)', width=1),
                        text=df_db['Letzter'].fillna(''), hovertemplate='%{x}: %{text}<extra></extra>'
                    ))
                    fig_db.add_hline(y=avg_s, line_dash='dash', line_color='rgba(255,215,0,0.4)',
                                      annotation_text=f"Ø Start {int(avg_s)}:{int((avg_s%1)*60):02d}",
                                      annotation_font_color='rgba(255,215,0,0.7)')
                    if avg_e:
                        fig_db.add_hline(y=avg_e, line_dash='dash', line_color='rgba(162,155,254,0.4)',
                                          annotation_text=f"Ø Ende {int(avg_e)}:{int((avg_e%1)*60):02d}",
                                          annotation_font_color='rgba(162,155,254,0.7)',
                                          annotation_position='top left')
                    fig_db.update_layout(
                        **_DARK, height=260,
                        yaxis=dict(title='Uhrzeit', tickvals=list(range(5,24)),
                                   ticktext=[f"{h}:00" for h in range(5,24)],
                                   range=[4,23], **_GRID),
                        margin=dict(t=10,b=30,l=55,r=10),
                        legend=dict(orientation='h', y=1.05)
                    )
                    st.plotly_chart(fig_db, use_container_width=True)
            else:
                st.info("Noch keine Tagesdaten")

        with cr7a:
            # ── Ø Task-Dauer nach Stunde ──────────────────────────
            st.subheader("⏱️ Ø Task-Dauer nach Stunde")
            if dur_by_hour:
                df_dh = pd.DataFrame(dur_by_hour, columns=['Stunde','avg_secs','n'])
                df_dh['avg_min'] = (df_dh['avg_secs'] / 60).round(0)
                peak_dur_h = int(df_dh.loc[df_dh['avg_min'].idxmax(), 'Stunde'])
                fig_dh = go.Figure(go.Bar(
                    x=[f"{int(h)}h" for h in df_dh['Stunde']], y=df_dh['avg_min'],
                    marker_color=['#ff9500' if int(h)==peak_dur_h else 'rgba(255,149,0,0.35)'
                                   for h in df_dh['Stunde']],
                    text=df_dh['avg_min'].astype(int), textposition='outside',
                    hovertemplate='%{x}: Ø %{y:.0f} Min (%{customdata} Tasks)<extra></extra>',
                    customdata=df_dh['n']
                ))
                fig_dh.update_layout(**_DARK, height=260, yaxis=dict(title='Ø Min', **_GRID),
                                      margin=dict(t=10,b=30,l=40,r=10))
                st.caption(f"Längste Tasks durchschnittlich: **{peak_dur_h}:00–{peak_dur_h+1}:00 Uhr**")
                st.plotly_chart(fig_dh, use_container_width=True)

        st.markdown("---")

        # ── Focus-Block Analyse (aus Fokus-Modus-Tracking) ───────────
        st.subheader("🎯 Pomodoro Focus-Blöcke")
        fb_all = get_focus_blocks(days=60)
        if fb_all:
            df_fb = pd.DataFrame(fb_all)
            df_fb['min'] = (df_fb['secs'] / 60).round(1)
            df_fb['steps_pct'] = df_fb.apply(
                lambda r: round(r['steps_done'] / r['steps_total'] * 100) if r['steps_total'] > 0 else 0, axis=1
            )

            total_blks     = len(df_fb)
            avg_dur        = df_fb['min'].mean()
            deep_blks      = (df_fb['min'] >= 20).sum()
            total_pomo_h   = round(df_fb['min'].sum() / 60, 1)
            avg_steps_rate = df_fb[df_fb['steps_total'] > 0]['steps_pct'].mean() if (df_fb['steps_total'] > 0).any() else 0

            b1, b2, b3, b4, b5 = st.columns(5)
            b1.metric("Blocks gesamt",    total_blks)
            b2.metric("Ø Block-Dauer",    f"{avg_dur:.0f} Min")
            b3.metric("Full Pomo (≥20 Min)", int(deep_blks))
            b4.metric("Gesamt Fokuszeit", f"{total_pomo_h}h")
            b5.metric("Ø Schritte-Rate",  f"{avg_steps_rate:.0f}%" if avg_steps_rate else "–")

            col_bh1, col_bh2 = st.columns([3, 2])
            with col_bh1:
                # Blocks per day with steps heatmap
                daily_fb = df_fb.groupby('date').agg(
                    blocks=('min','count'), fokus_min=('min','sum'),
                    avg_steps=('steps_pct','mean')
                ).reset_index()

                fig_fb_d = go.Figure()
                fig_fb_d.add_trace(go.Bar(
                    x=daily_fb['date'], y=daily_fb['blocks'],
                    name='Blöcke', marker_color='rgba(162,155,254,0.7)',
                    hovertemplate='%{x}: %{y} Blöcke | %{customdata:.0f} Min<extra></extra>',
                    customdata=daily_fb['fokus_min']
                ))
                fig_fb_d.add_trace(go.Scatter(
                    x=daily_fb['date'], y=daily_fb['avg_steps'],
                    name='Ø Schritte %', yaxis='y2',
                    line=dict(color='#ffd700', width=2), mode='lines+markers',
                    hovertemplate='%{x}: %{y:.0f}% Schritte<extra></extra>'
                ))
                fig_fb_d.update_layout(
                    **_DARK, height=240, hovermode='x unified',
                    yaxis=dict(title='Blöcke', **_GRID),
                    yaxis2=dict(title='Schritte %', overlaying='y', side='right', range=[0,110], **_GRID),
                    margin=dict(t=10,b=30,l=40,r=50),
                    legend=dict(orientation='h', y=1.05)
                )
                st.plotly_chart(fig_fb_d, use_container_width=True)

            with col_bh2:
                st.caption("Letzte Fokus-Sessions")
                rs_fb = ("background:rgba(255,255,255,0.03);border-radius:8px;padding:7px 11px;"
                         "margin-bottom:5px;font-size:11px")
                for blk in fb_all[:7]:
                    dur_m = round(blk['secs'] / 60)
                    steps_str = (f"✅ {blk['steps_done']}/{blk['steps_total']}"
                                 if blk['steps_total'] > 0 else "")
                    task_short = blk['task'][:28] + '…' if len(blk['task']) > 28 else blk['task']
                    st.markdown(
                        f'<div style="{rs_fb}">'
                        f'<div style="font-weight:600;color:white">{task_short}</div>'
                        f'<div style="color:rgba(255,255,255,0.4)">{blk["date"]} · R{blk["round"]} · '
                        f'{dur_m} Min {steps_str}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
        else:
            st.info("Noch keine Fokus-Blöcke — starte eine Aufgabe im Fokus-Modus um das Tracking zu aktivieren.")

        st.markdown("---")

        # ── Session-Längen + Context-Switch ──────────────────────
        col_sl, col_cs = st.columns(2)

        with col_sl:
            st.subheader("📊 Session-Längen Verteilung")
            if dur_rows:
                df_dur = pd.DataFrame(dur_rows, columns=['Secs','Typ'])
                df_dur['Min'] = df_dur['Secs'] / 60
                type_colors_d = {'brain':'#00d4ff','highlight':'#ffd700','micro':'#ff6b6b','projekt':'#a29bfe'}
                fig_dur = go.Figure()
                for typ in df_dur['Typ'].unique():
                    sub = df_dur[df_dur['Typ']==typ]
                    fig_dur.add_trace(go.Histogram(
                        x=sub['Min'], name=typ, nbinsx=30, opacity=0.72,
                        marker_color=type_colors_d.get(typ,'#dfe6e9'),
                        hovertemplate='%{x:.0f} Min: %{y}<extra></extra>'
                    ))
                avg_dur_all = df_dur['Min'].mean()
                fig_dur.add_vline(x=avg_dur_all, line_dash='dash', line_color='#2ecc71',
                                   annotation_text=f"Ø {avg_dur_all:.0f} Min",
                                   annotation_font_color='#2ecc71')
                fig_dur.update_layout(
                    **_DARK, barmode='overlay', height=240,
                    xaxis=dict(title='Dauer (Min)', range=[0,120], **_GRID),
                    yaxis=dict(title='Sessions', **_GRID),
                    margin=dict(t=10,b=40,l=40,r=10),
                    legend=dict(orientation='h', y=1.05)
                )
                st.plotly_chart(fig_dur, use_container_width=True)

        with col_cs:
            st.subheader("🔀 Context-Switch Analyse")
            if switches:
                switch_count = sum(1 for r in switches if r[1] and r[2] and r[1] != r[2])
                no_switch    = sum(1 for r in switches if r[1] and r[2] and r[1] == r[2])
                no_prev      = sum(1 for r in switches if not r[2])

                pairs = {}
                for r in switches:
                    if r[1] and r[2] and r[1] != r[2]:
                        key = f"{r[2]} → {r[1]}"
                        pairs[key] = pairs.get(key, 0) + 1

                pct_switch = switch_count / (switch_count + no_switch) * 100 if (switch_count + no_switch) else 0
                st.metric("Context-Switches",   switch_count)
                st.metric("Gleicher Typ (Flow)", no_switch)
                st.metric("Switch-Rate",         f"{pct_switch:.0f}%")

                if pairs:
                    top_pairs = sorted(pairs.items(), key=lambda x: x[1], reverse=True)[:5]
                    st.caption("Häufigste Wechsel:")
                    rs_sw = ("background:rgba(255,255,255,0.03);border-radius:7px;padding:6px 10px;"
                             "margin-bottom:5px;font-size:11px;display:flex;justify-content:space-between")
                    for label, cnt in top_pairs:
                        st.markdown(
                            f'<div style="{rs_sw}">'
                            f'<span style="color:rgba(255,255,255,0.7)">{label}</span>'
                            f'<span style="color:#74b9ff;font-weight:700">×{cnt}</span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )

    # ══════════════════════════════════════════════════════════════
    # TAB 8 — KI ANALYSE
    # ══════════════════════════════════════════════════════════════
    with tab8:
        st.subheader("🤖 KI-Statistik-Analyse")
        st.caption("Die KI analysiert alle deine Daten, erkennt Muster und zeigt konkret was nicht funktioniert — mit spezifischen Lösungen.")

        cache_key = f"ki_stats_{date.today().isoformat()}"
        cached_raw = get_setting(cache_key)
        cached_analysis = None
        if cached_raw:
            try:
                cached_analysis = json.loads(cached_raw)
            except Exception:
                pass

        col_ki_info, col_ki_btn = st.columns([3, 1])
        with col_ki_info:
            if cached_analysis and 'error' not in cached_analysis:
                st.success(f"Analyse von heute geladen. Klicke 'Neu analysieren' für eine frische Auswertung.")
        with col_ki_btn:
            run_ki = st.button("🔍 Neu analysieren", key="ki_stats_run", use_container_width=True)

        if run_ki:
            api_key_ki = get_setting("nvidia_api_key") or ""
            if not api_key_ki:
                st.error("Kein API-Key hinterlegt — in den Einstellungen eintragen.")
            else:
                with st.spinner("KI analysiert alle deine Daten... (ca. 10-20s)"):
                    result_ki = ki_analyze_statistics(api_key_ki)
                    if 'error' not in result_ki:
                        set_setting(cache_key, json.dumps(result_ki, ensure_ascii=False))
                        cached_analysis = result_ki
                        st.rerun()
                    else:
                        st.error(f"Fehler: {result_ki['error']}")

        if cached_analysis and 'error' not in cached_analysis:
            an = cached_analysis

            # Top Pattern Banner
            if an.get('top_pattern'):
                st.markdown(
                    f'<div style="background:linear-gradient(135deg,rgba(0,212,255,0.1),rgba(162,155,254,0.07));\n'
                    f'border-radius:14px;padding:16px 22px;border:1px solid rgba(0,212,255,0.25);margin:12px 0 20px 0">\n'
                    f'<div style="font-size:10px;color:rgba(0,212,255,0.7);font-weight:700;letter-spacing:1.5px;margin-bottom:6px">WICHTIGSTES MUSTER</div>\n'
                    f'<div style="font-size:15px;font-weight:700;color:white;line-height:1.5">{an["top_pattern"]}</div>\n'
                    f'</div>',
                    unsafe_allow_html=True
                )

            col_pat, col_prob = st.columns(2)

            with col_pat:
                st.markdown("**📊 Erkannte Muster**")
                type_border = {'positive':'#2ecc71','negative':'#e74c3c','neutral':'#f39c12'}
                for pat in an.get('patterns', []):
                    bc = type_border.get(pat.get('type','neutral'),'#74b9ff')
                    st.markdown(
                        f'<div style="border-left:3px solid {bc};background:rgba(255,255,255,0.025);\n'
                        f'border-radius:0 10px 10px 0;padding:10px 14px;margin-bottom:9px">\n'
                        f'<div style="font-weight:700;color:white;font-size:13px">{pat.get("icon","📈")} {pat.get("title","")}</div>\n'
                        f'<div style="color:rgba(255,255,255,0.5);font-size:11px;margin-top:3px;line-height:1.5">{pat.get("evidence","")}</div>\n'
                        f'</div>',
                        unsafe_allow_html=True
                    )

            with col_prob:
                st.markdown("**⚠️ Was nicht funktioniert**")
                sev_c = {'hoch':'#e74c3c','mittel':'#f39c12','niedrig':'#74b9ff'}
                for prob in an.get('problems', []):
                    sc = sev_c.get(prob.get('severity','mittel'),'#f39c12')
                    st.markdown(
                        f'<div style="background:rgba(255,255,255,0.025);border:1px solid {sc}44;\n'
                        f'border-radius:10px;padding:10px 14px;margin-bottom:9px">\n'
                        f'<div style="display:flex;align-items:center;gap:8px">\n'
                        f'<span>{prob.get("icon","⚠️")}</span>\n'
                        f'<span style="font-weight:700;color:white;font-size:13px">{prob.get("title","")}</span>\n'
                        f'<span style="margin-left:auto;font-size:10px;font-weight:700;color:{sc};\n'
                        f'background:{sc}22;padding:2px 8px;border-radius:4px">{prob.get("severity","?").upper()}</span>\n'
                        f'</div>\n'
                        f'<div style="color:rgba(255,255,255,0.5);font-size:11px;margin-top:4px;line-height:1.5">{prob.get("evidence","")}</div>\n'
                        f'</div>',
                        unsafe_allow_html=True
                    )

            st.markdown("---")

            # Lösungen
            st.markdown("**🎯 Konkrete Lösungen**")
            solutions = an.get('solutions', [])
            if solutions:
                sol_cols = st.columns(min(len(solutions), 3))
                for i, sol in enumerate(solutions):
                    with sol_cols[i % 3]:
                        st.markdown(
                            f'<div style="background:rgba(46,204,113,0.05);border:1px solid rgba(46,204,113,0.2);\n'
                            f'border-radius:12px;padding:14px 16px;margin-bottom:8px;min-height:140px">\n'
                            f'<div style="font-size:22px;margin-bottom:6px">{sol.get("icon","💡")}</div>\n'
                            f'<div style="font-weight:700;color:white;font-size:13px;margin-bottom:4px">{sol.get("action","")}</div>\n'
                            f'<div style="color:rgba(255,255,255,0.35);font-size:10px;font-style:italic;margin-bottom:6px">↳ {sol.get("problem","")}</div>\n'
                            f'<div style="color:rgba(255,255,255,0.6);font-size:11px;line-height:1.5">{sol.get("why","")}</div>\n'
                            f'</div>',
                            unsafe_allow_html=True
                        )

            # Korrelationen
            correlations = an.get('correlations', [])
            if correlations:
                st.markdown("---")
                st.markdown("**🔗 Erkannte Zusammenhänge**")
                corr_cols = st.columns(min(len(correlations), 3))
                for i, corr in enumerate(correlations):
                    with corr_cols[i % 3]:
                        st.markdown(
                            f'<div style="background:rgba(116,185,255,0.06);border:1px solid rgba(116,185,255,0.18);\n'
                            f'border-radius:12px;padding:12px 14px;margin-bottom:8px">\n'
                            f'<div style="font-size:18px;margin-bottom:5px">{corr.get("icon","🔗")}</div>\n'
                            f'<div style="font-size:12px;color:#74b9ff;margin-bottom:3px">'
                            f'<strong>{corr.get("factor_a","")}</strong> × <strong>{corr.get("factor_b","")}</strong></div>\n'
                            f'<div style="color:rgba(255,255,255,0.65);font-size:11px;line-height:1.5">{corr.get("insight","")}</div>\n'
                            f'</div>',
                            unsafe_allow_html=True
                        )

            # Energie-Insight
            if an.get('energy_insight'):
                st.markdown("---")
                st.markdown(
                    f'<div style="background:rgba(255,149,0,0.07);border:1px solid rgba(255,149,0,0.22);\n'
                    f'border-radius:12px;padding:14px 20px">\n'
                    f'<div style="font-size:10px;color:rgba(255,149,0,0.8);font-weight:700;letter-spacing:1.5px;margin-bottom:7px">⚡ DEINE OPTIMALE TAGESSTRUKTUR</div>\n'
                    f'<div style="color:white;font-size:13px;line-height:1.7">{an["energy_insight"]}</div>\n'
                    f'</div>',
                    unsafe_allow_html=True
                )

        elif not cached_analysis:
            st.markdown(
                '<div style="text-align:center;padding:70px 20px;color:rgba(255,255,255,0.25)">'
                '<div style="font-size:56px;margin-bottom:14px">🤖</div>'
                '<div style="font-size:17px;font-weight:600">KI-Analyse noch nicht gestartet</div>'
                '<div style="font-size:12px;margin-top:8px">Klicke "Neu analysieren" — die KI wertet alle gesammelten Daten aus:<br>'
                'Produktivitätsmuster, Schlaf-Korrelationen, Habit-Konsistenz, Trainings-Trends</div>'
                '</div>',
                unsafe_allow_html=True
            )


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
    prog = get_cal_progress()
    today_tracks = todays_cal_tracks()
    today_plan   = get_stored_training_plan() or {}
    rest_day     = today_plan.get('rest_day', False)
    api_key      = get_setting('nvidia_api_key', '')

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

    # ── Heutiger Plan ──────────────────────────────────────────────
    plan_src = today_plan.get('source', 'auto')
    src_badge = '🤖 KI-Plan' if plan_src == 'ki' else ('✋ Manuell' if plan_src == 'manual' else '⚙️ Auto-Plan')
    src_color = '#00d4ff' if plan_src == 'ki' else ('#ffd700' if plan_src == 'manual' else '#a29bfe')
    rationale = today_plan.get('rationale', '')
    tip = today_plan.get('tip', '')

    if rest_day:
        st.markdown(f"""<div style="background:rgba(155,89,182,0.1);border:1px solid rgba(155,89,182,0.35);
            border-radius:14px;padding:18px 22px;margin-bottom:16px">
            <div style="font-size:20px;font-weight:900;color:#a29bfe;margin-bottom:6px">😴 Heute ist Ruhetag</div>
            <div style="font-size:13px;color:rgba(255,255,255,0.65)">{rationale}</div>
            <div style="font-size:11px;color:rgba(255,255,255,0.3);margin-top:8px">
              Aktive Regeneration: leichtes Spazieren, Dehnen — oder einfach erholen.</div>
        </div>""", unsafe_allow_html=True)
    else:
        track_chips = " ".join(
            f'<span style="background:{CAL_TRACKS[t]["color"]}22;color:{CAL_TRACKS[t]["color"]};'
            f'border:1px solid {CAL_TRACKS[t]["color"]}55;border-radius:10px;'
            f'padding:2px 10px;font-size:11px;font-weight:700">'
            f'{CAL_TRACKS[t]["icon"]} {CAL_TRACKS[t]["label"]}</span>'
            for t in today_tracks if t in CAL_TRACKS
        )
        st.markdown(f"""<div style="background:rgba(0,212,255,0.05);border:1px solid rgba(0,212,255,0.18);
            border-radius:14px;padding:16px 20px;margin-bottom:14px">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap">
              <span style="font-size:13px;font-weight:800;color:white">Heute trainierst du:</span>
              {track_chips}
              <span style="font-size:10px;color:{src_color};background:{src_color}18;
                    border:1px solid {src_color}44;padding:2px 8px;border-radius:8px">{src_badge}</span>
            </div>
            {f'<div style="font-size:12px;color:rgba(255,255,255,0.5);font-style:italic">{rationale}</div>' if rationale else ''}
            {f'<div style="font-size:12px;color:#ffd700;margin-top:6px">💡 {tip}</div>' if tip else ''}
        </div>""", unsafe_allow_html=True)

    # KI / Rest-Day Steuerung
    ki_col, rest_col = st.columns(2)
    with ki_col:
        if st.button(
            "🤖 KI-Plan neu erstellen" if api_key else "🤖 KI-Plan (API-Key fehlt)",
            key="train_ki_plan_btn", use_container_width=True, disabled=not api_key
        ):
            with st.spinner("KI analysiert deine gesamten Trainingsdaten und erstellt deinen perfekten Plan …"):
                ki_result = ki_generate_daily_exercises(api_key)
            if ki_result and not ki_result.get('error'):
                today_str = date.today().isoformat()
                if ki_result.get('rest_day'):
                    save_training_plan({'tracks': [], 'rest_day': True, 'source': 'ki',
                                        'rationale': ki_result.get('day_rationale', ''),
                                        'tip': ki_result.get('tip', '')})
                    update_todays_training_entry([])
                else:
                    tracks_data = ki_result.get('tracks', [])
                    save_daily_exercises(today_str, tracks_data, meta={
                        'rest_day': False, 'source': 'ki',
                        'rationale': ki_result.get('day_rationale', ''),
                        'weekly_focus': ki_result.get('weekly_focus', ''),
                        'tip': ki_result.get('tip', '')
                    })
                    update_todays_training_entry([td['track'] for td in tracks_data])
                st.toast("Neuer KI-Trainingsplan erstellt!", icon="🤖")
                st.rerun()
            elif ki_result and ki_result.get('error'):
                st.error(f"KI-Fehler: {ki_result['error']}")
    with rest_col:
        if rest_day:
            if st.button("💪 Doch trainieren", key="train_undo_rest_btn", use_container_width=True):
                today_str = date.today().isoformat()
                conn_r = sqlite3.connect(DB_PATH)
                conn_r.execute("DELETE FROM settings WHERE key=?", (f"training_plan_{today_str}",))
                conn_r.execute("DELETE FROM daily_training_exercises WHERE plan_date=?", (today_str,))
                conn_r.commit()
                conn_r.close()
                st.rerun()
        else:
            if st.button("😴 Als Ruhetag markieren", key="train_rest_day_btn", use_container_width=True):
                today_str = date.today().isoformat()
                save_training_plan({'tracks': [], 'rest_day': True, 'source': 'manual',
                                    'rationale': 'Manuell als Ruhetag markiert.'})
                conn_r = sqlite3.connect(DB_PATH)
                conn_r.execute("DELETE FROM daily_training_exercises WHERE plan_date=?", (today_str,))
                conn_r.commit()
                conn_r.close()
                update_todays_training_entry([])
                st.rerun()

    # ── Heutiges Training ──────────────────────────────────────────
    ki_exercises = get_daily_exercises()  # {track: [exercise_dicts]}
    has_ki_plan = bool(ki_exercises)

    if not rest_day:
        if not has_ki_plan and not today_tracks:
            st.markdown("---")
            st.markdown("""<div style="text-align:center;padding:32px;background:rgba(0,212,255,0.04);
                border:1px dashed rgba(0,212,255,0.25);border-radius:16px;margin-top:8px">
                <div style="font-size:32px;margin-bottom:12px">🤖</div>
                <div style="font-size:16px;font-weight:800;color:white;margin-bottom:8px">Noch kein KI-Plan für heute</div>
                <div style="font-size:13px;color:rgba(255,255,255,0.5)">Klicke oben auf <strong>KI-Plan neu erstellen</strong> — die KI analysiert deine gesamte Trainingshistorie und erstellt den perfekt auf dich zugeschnittenen Plan für heute.</div>
            </div>""", unsafe_allow_html=True)

        elif has_ki_plan:
            st.markdown("### 💪 Dein heutiges Training")
            entry_id, entry_done = get_todays_training_entry_id()

            if streak['trained_today']:
                st.success("Heute bereits geloggt — stark! Du kannst unten trotzdem nachtragen.")

            # Wochenfoukus & Tipp aus dem gespeicherten Plan
            stored_wf = today_plan.get('weekly_focus', '')
            if stored_wf:
                st.markdown(f"""<div style="background:rgba(255,215,0,0.07);border-left:3px solid #ffd700;
                    border-radius:0 10px 10px 0;padding:10px 16px;margin-bottom:16px;font-size:12.5px;color:rgba(255,255,255,0.75)">
                    <strong style="color:#ffd700">Wochenfokus:</strong> {stored_wf}</div>""",
                    unsafe_allow_html=True)

            # ── KI Trainingsbriefing ───────────────────────────────────
            today_str_b = date.today().isoformat()
            briefing_key = f"training_briefing_{today_str_b}"
            briefing_cached = get_setting(briefing_key)
            briefing_data = None
            if briefing_cached:
                try:
                    briefing_data = json.loads(briefing_cached)
                except Exception:
                    pass

            brief_col, new_col = st.columns([3, 1])
            with brief_col:
                st.markdown("#### 🧠 KI Trainingsbriefing")
            with new_col:
                if api_key:
                    if st.button("🔄 Neu", key="briefing_regen_btn", use_container_width=True):
                        conn_b = sqlite3.connect(DB_PATH)
                        conn_b.execute("DELETE FROM settings WHERE key=?", (briefing_key,))
                        conn_b.commit()
                        conn_b.close()
                        with st.spinner("KI analysiert…"):
                            briefing_data = ki_training_briefing(api_key)
                        st.rerun()

            if not briefing_data and api_key:
                if st.button("🧠 KI Briefing erstellen", key="briefing_gen_btn", use_container_width=True):
                    with st.spinner("KI analysiert dein Training tief…"):
                        briefing_data = ki_training_briefing(api_key)
                    st.rerun()

            if briefing_data and not briefing_data.get('error'):
                # Übergeordnetes Ziel
                ueberziel = briefing_data.get('ueberziel', '')
                if ueberziel:
                    st.markdown(f"""<div style="background:linear-gradient(135deg,rgba(0,212,255,0.08),rgba(155,89,182,0.08));
                        border:1px solid rgba(0,212,255,0.25);border-radius:14px;padding:18px 22px;margin-bottom:14px">
                        <div style="font-size:11px;font-weight:700;color:rgba(0,212,255,0.7);letter-spacing:1.5px;margin-bottom:8px">
                          🎯 ÜBERGEORDNETES ZIEL</div>
                        <div style="font-size:14px;color:rgba(255,255,255,0.9);line-height:1.6">{ueberziel}</div>
                    </div>""", unsafe_allow_html=True)

                # Meilensteine
                milestones = briefing_data.get('meilensteine', [])
                if milestones:
                    ms_html = ""
                    for ms in milestones:
                        status = ms.get('status', 'offen')
                        if status == 'erreicht':
                            s_color, s_icon, s_bg = '#2ecc71', '✅', 'rgba(46,204,113,0.08)'
                            s_border = 'rgba(46,204,113,0.3)'
                        elif status == 'in_arbeit':
                            s_color, s_icon, s_bg = '#00d4ff', '⚡', 'rgba(0,212,255,0.08)'
                            s_border = 'rgba(0,212,255,0.35)'
                        else:
                            s_color, s_icon, s_bg = 'rgba(255,255,255,0.3)', '○', 'rgba(255,255,255,0.03)'
                            s_border = 'rgba(255,255,255,0.1)'
                        ms_html += f"""<div style="background:{s_bg};border:1px solid {s_border};
                            border-radius:10px;padding:12px 16px;margin-bottom:8px">
                            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                              <span style="font-size:14px">{s_icon}</span>
                              <span style="font-size:13px;font-weight:800;color:{s_color}">{ms.get('name','')}</span>
                              <span style="font-size:10px;color:{s_color};background:{s_color}18;
                                padding:1px 7px;border-radius:6px;margin-left:auto">{status.upper()}</span>
                            </div>
                            <div style="font-size:12px;color:rgba(255,255,255,0.6);line-height:1.5">{ms.get('beschreibung','')}</div>
                            {f'<div style="font-size:11px;color:{s_color};margin-top:5px;font-weight:600">→ {ms.get("stand","")}</div>' if ms.get('stand') else ''}
                        </div>"""
                    st.markdown(f"""<div style="margin-bottom:14px">
                        <div style="font-size:11px;font-weight:700;color:rgba(255,215,0,0.7);letter-spacing:1.5px;margin-bottom:8px">
                          🏆 MEILENSTEINE</div>
                        {ms_html}
                    </div>""", unsafe_allow_html=True)

                # Ziel heute + Warum
                ziel_heute = briefing_data.get('ziel_heute', '')
                warum_heute = briefing_data.get('warum_heute', '')
                verbindung = briefing_data.get('verbindung_zum_ziel', '')
                if ziel_heute:
                    st.markdown(f"""<div style="background:rgba(255,215,0,0.07);border:1px solid rgba(255,215,0,0.25);
                        border-radius:14px;padding:16px 20px;margin-bottom:14px">
                        <div style="font-size:11px;font-weight:700;color:rgba(255,215,0,0.7);letter-spacing:1.5px;margin-bottom:8px">
                          ⚡ ZIEL HEUTE</div>
                        <div style="font-size:15px;font-weight:800;color:#ffd700;margin-bottom:10px">{ziel_heute}</div>
                        {f'<div style="font-size:12.5px;color:rgba(255,255,255,0.7);line-height:1.6;margin-bottom:8px">{warum_heute}</div>' if warum_heute else ''}
                        {f'<div style="font-size:12px;color:rgba(0,212,255,0.8);line-height:1.6;border-top:1px solid rgba(255,255,255,0.08);padding-top:8px;margin-top:4px">🔗 {verbindung}</div>' if verbindung else ''}
                    </div>""", unsafe_allow_html=True)

                # Übungen mit tiefen Erklärungen
                uebungen = briefing_data.get('uebungen', [])
                if uebungen:
                    st.markdown("""<div style="font-size:11px;font-weight:700;color:rgba(255,255,255,0.5);
                        letter-spacing:1.5px;margin-bottom:10px">📋 ÜBUNGEN IM DETAIL</div>""",
                        unsafe_allow_html=True)
                    for ub in uebungen:
                        track_label = ub.get('track', '')
                        track_color = '#00d4ff'
                        for tk, ti in CAL_TRACKS.items():
                            if ti['label'].lower() in track_label.lower() or track_label.lower() in ti['label'].lower():
                                track_color = ti['color']
                                break
                        with st.expander(f"**{ub.get('name','')}** — {track_label}", expanded=False):
                            cols_ub = st.columns(2)
                            with cols_ub[0]:
                                was = ub.get('was_trainiert', '')
                                if was:
                                    st.markdown(f"""<div style="background:rgba(255,255,255,0.04);border-radius:10px;
                                        padding:12px;margin-bottom:8px">
                                        <div style="font-size:10px;font-weight:700;color:rgba(255,255,255,0.4);
                                          letter-spacing:1px;margin-bottom:5px">💪 WAS WIRD TRAINIERT</div>
                                        <div style="font-size:12px;color:rgba(255,255,255,0.8);line-height:1.5">{was}</div>
                                    </div>""", unsafe_allow_html=True)
                                bio = ub.get('biomechanik', '')
                                if bio:
                                    st.markdown(f"""<div style="background:rgba(255,255,255,0.04);border-radius:10px;
                                        padding:12px">
                                        <div style="font-size:10px;font-weight:700;color:rgba(255,255,255,0.4);
                                          letter-spacing:1px;margin-bottom:5px">⚙️ BIOMECHANIK</div>
                                        <div style="font-size:12px;color:rgba(255,255,255,0.8);line-height:1.5">{bio}</div>
                                    </div>""", unsafe_allow_html=True)
                            with cols_ub[1]:
                                warum = ub.get('warum_jetzt', '')
                                if warum:
                                    st.markdown(f"""<div style="background:rgba(0,212,255,0.05);border-radius:10px;
                                        padding:12px;margin-bottom:8px;border:1px solid rgba(0,212,255,0.15)">
                                        <div style="font-size:10px;font-weight:700;color:rgba(0,212,255,0.6);
                                          letter-spacing:1px;margin-bottom:5px">🎯 WARUM JETZT</div>
                                        <div style="font-size:12px;color:rgba(255,255,255,0.8);line-height:1.5">{warum}</div>
                                    </div>""", unsafe_allow_html=True)
                                langzeit = ub.get('langzeitwirkung', '')
                                if langzeit:
                                    st.markdown(f"""<div style="background:rgba(46,204,113,0.05);border-radius:10px;
                                        padding:12px;border:1px solid rgba(46,204,113,0.15)">
                                        <div style="font-size:10px;font-weight:700;color:rgba(46,204,113,0.6);
                                          letter-spacing:1px;margin-bottom:5px">📈 LANGZEITWIRKUNG</div>
                                        <div style="font-size:12px;color:rgba(255,255,255,0.8);line-height:1.5">{langzeit}</div>
                                    </div>""", unsafe_allow_html=True)
                            mental = ub.get('mental_cue', '')
                            if mental:
                                st.markdown(f"""<div style="background:rgba(255,215,0,0.06);border-radius:8px;
                                    padding:10px 14px;margin-top:4px;border-left:3px solid #ffd700">
                                    <span style="font-size:11px;font-weight:700;color:#ffd700">🧠 MENTAL CUE: </span>
                                    <span style="font-size:12px;color:rgba(255,255,255,0.85);font-style:italic">{mental}</span>
                                </div>""", unsafe_allow_html=True)

                # Coach-Wort
                coach_wort = briefing_data.get('coach_wort', '')
                if coach_wort:
                    st.markdown(f"""<div style="background:rgba(155,89,182,0.08);border:1px solid rgba(155,89,182,0.3);
                        border-radius:12px;padding:14px 18px;margin-bottom:18px">
                        <span style="font-size:11px;font-weight:700;color:#a29bfe">🎙️ COACH: </span>
                        <span style="font-size:13px;color:rgba(255,255,255,0.85);font-style:italic">{coach_wort}</span>
                    </div>""", unsafe_allow_html=True)

            st.markdown("---")

            with st.form("ki_log_form"):
                inputs = {}
                for track, exercises in ki_exercises.items():
                    info = CAL_TRACKS.get(track, {'icon': '🏋️', 'color': '#aaaaaa', 'label': track})
                    track_color = info['color']
                    track_icon = info['icon']
                    track_label = info['label']
                    st.markdown(f"""<div style="margin:20px 0 10px 0;display:flex;align-items:center;gap:10px">
                        <span style="font-size:22px">{track_icon}</span>
                        <span style="font-size:16px;font-weight:900;color:{track_color}">{track_label}</span>
                    </div>""", unsafe_allow_html=True)
                    inputs[track] = []
                    for i, ex in enumerate(exercises):
                        is_hold = ex['hold_seconds'] > 0
                        unit = "Sek" if is_hold else "Wdh"
                        target_val = ex['hold_seconds'] if is_hold else ex['reps']
                        diff_color = '#2ecc71' if ex['difficulty'] <= 3 else ('#f39c12' if ex['difficulty'] <= 6 else '#e74c3c')
                        diff_label = '🟢 Leicht' if ex['difficulty'] <= 3 else ('🟡 Mittel' if ex['difficulty'] <= 6 else '🔴 Hart')
                        st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid {track_color}33;
                            border-radius:12px;padding:14px 16px;margin-bottom:8px">
                            <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:6px">
                              <div>
                                <div style="font-size:14px;font-weight:800;color:white">{ex['name']}</div>
                                <div style="font-size:11px;color:rgba(255,255,255,0.45);margin-top:3px">
                                  Ziel: {ex['sets']} Sätze × {target_val} {unit}</div>
                              </div>
                              <span style="font-size:10px;color:{diff_color};background:{diff_color}18;
                                padding:3px 9px;border-radius:8px;border:1px solid {diff_color}44;white-space:nowrap">{diff_label}</span>
                            </div>
                            {f'<div style="font-size:11.5px;color:{track_color};margin-top:8px;font-style:italic">⚡ {ex["cue"]}</div>' if ex.get("cue") else ''}
                            {f'<div style="font-size:11px;color:rgba(255,255,255,0.4);margin-top:4px">→ {ex["why"]}</div>' if ex.get("why") else ''}
                        </div>""", unsafe_allow_html=True)
                        ec1, ec2 = st.columns(2)
                        with ec1:
                            sets_done = st.number_input(
                                "Sätze geschafft", min_value=0, max_value=ex['sets'] + 3,
                                value=ex['sets'], key=f"ki_sets_{track}_{i}")
                        with ec2:
                            perf_done = st.number_input(
                                f"Beste Leistung ({unit})", min_value=0,
                                max_value=max(target_val * 3, target_val + 30),
                                value=target_val, key=f"ki_perf_{track}_{i}")
                        inputs[track].append({
                            'ex': ex, 'sets_done': sets_done, 'perf_done': perf_done,
                            'is_hold': is_hold, 'target_val': target_val
                        })

                notes = st.text_input("Notiz (optional)", key="ki_notes",
                                       placeholder="z.B. heute schwer, wenig Schlaf")
                submitted = st.form_submit_button("✅ Training abschließen",
                                                   use_container_width=True, type="primary")

            if submitted:
                today_str = date.today().isoformat()
                clean_count = 0
                total_exercises = 0
                for track, ex_inputs in inputs.items():
                    for inp in ex_inputs:
                        ex = inp['ex']
                        clean = log_ki_exercise(
                            today_str, track, ex['name'],
                            inp['sets_done'], inp['perf_done'],
                            ex['sets'], inp['target_val'],
                            is_hold=inp['is_hold'], notes=notes
                        )
                        total_exercises += 1
                        if clean:
                            clean_count += 1

                points = 40 * clean_count + 15 * (total_exercises - clean_count)
                entry_id, _ = get_todays_training_entry_id()
                if entry_id:
                    toggle_done(entry_id, True, points=points)
                else:
                    sync_daily_training()
                    entry_id, _ = get_todays_training_entry_id()
                    if entry_id:
                        toggle_done(entry_id, True, points=points)

                st.balloons()
                st.success(f"Training geloggt — {clean_count}/{total_exercises} Übungen sauber, +{points} Punkte!")
                time.sleep(0.3)
                st.rerun()

        else:
            # Fallback: alter Track-basierter Plan (noch kein KI-Exercices-Plan, aber tracks bekannt)
            st.markdown("### 💪 Heutiges Training")
            entry_id, entry_done = get_todays_training_entry_id()
            if streak['trained_today']:
                st.success("Heute bereits geloggt — stark!")
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
                            "Sätze geschafft", min_value=0, max_value=ex['sets'] + 2, value=ex['sets'],
                            key=f"cal_sets_{track}")
                    with ic2:
                        inputs[track]['best'] = st.number_input(
                            f"Beste Leistung ({unit})", min_value=0, max_value=ex['target_reps'] * 3 + 10,
                            value=ex['target_reps'], key=f"cal_best_{track}")
                notes = st.text_input("Notiz (optional)", key="cal_notes",
                                       placeholder="z.B. heute schwer, wenig Schlaf")
                submitted = st.form_submit_button("✅ Training abschließen",
                                                   use_container_width=True, type="primary")
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
                st.success(f"Training geloggt — {clean_count}/{len(today_tracks)} sauber, +{points} Punkte!")
                for track, new_name in level_ups:
                    st.markdown(f"""<div style="background:linear-gradient(135deg,rgba(255,215,0,0.15),rgba(255,149,0,0.1));
                        border:1px solid rgba(255,215,0,0.5);border-radius:12px;padding:14px 18px;margin-top:8px">
                        <span style="font-size:18px">⬆️</span>
                        <strong style="color:#ffd700">Level-Up: {CAL_TRACKS[track]['label']}!</strong><br>
                        <span style="color:rgba(255,255,255,0.7);font-size:13px">
                          Neue Übung: <strong>{new_name}</strong></span>
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
    st.markdown("### 🤖 KI Trainingscoach (Muster-Analyse)")
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
        render_evening_routine_checklist(today_str)

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


def _render_household_section(status_all, frequency, today_str, show_label=True):
    tasks = [t for t in status_all if t['frequency'] == frequency]
    if not tasks:
        return
    if show_label:
        st.markdown(f"#### {HOUSEHOLD_FREQUENCY_LABELS[frequency]}")
    for t in tasks:
        is_custom = t.get('is_custom', False)
        cols = st.columns([0.44, 0.26, 0.20, 0.10])
        with cols[0]:
            st.markdown(
                f"{t['icon']} **{t['label']}** "
                f"<span style='font-size:10px;color:rgba(255,255,255,0.35)'>~{t['est_minutes']} Min</span>",
                unsafe_allow_html=True
            )
        with cols[1]:
            st.markdown(_household_status_badge(t), unsafe_allow_html=True)
        with cols[2]:
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
        with cols[3]:
            if is_custom:
                if st.button("🗑️", key=f"hh_del_{t['key']}", help="Aufgabe löschen"):
                    delete_custom_household_task(t['key'])
                    st.rerun()
            else:
                if st.button("🙈", key=f"hh_hide_{t['key']}", help="Ausblenden"):
                    hide_builtin_household_task(t['key'])
                    st.rerun()


def render_haushalt_page():
    st.title("🏡 Haushalt")

    today_str   = date.today().isoformat()
    status_all  = get_household_status()
    clean_score = household_clean_score()
    wohlfuehl   = household_wohlfuehl_index()
    streak      = get_household_daily_streak()

    st.markdown(_household_score_hero_html(clean_score, wohlfuehl), unsafe_allow_html=True)

    # ── Sync-Status & To-Do Info ──────────────────────────────────
    conn_hh = sqlite3.connect(DB_PATH)
    hh_in_todos = conn_hh.execute(
        "SELECT COUNT(*) FROM entries WHERE entry_date=? AND tags LIKE '%haushalt%' AND done=0",
        (today_str,)
    ).fetchone()[0]
    hh_done_today = conn_hh.execute(
        "SELECT COUNT(*) FROM entries WHERE entry_date=? AND tags LIKE '%haushalt%' AND done=1",
        (today_str,)
    ).fetchone()[0]
    conn_hh.close()

    due_count = sum(1 for t in status_all if t.get('due'))
    st.markdown(
        f'<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);'
        f'border-radius:12px;padding:12px 18px;margin:10px 0;display:flex;gap:20px;flex-wrap:wrap">'
        f'<div style="font-size:12px">'
        f'<span style="color:rgba(255,255,255,0.4)">Fällig heute:</span> '
        f'<strong style="color:#ff6b6b">{due_count}</strong></div>'
        f'<div style="font-size:12px">'
        f'<span style="color:rgba(255,255,255,0.4)">In To-Do-Liste:</span> '
        f'<strong style="color:#00d4ff">{hh_in_todos} offen</strong>, {hh_done_today} erledigt</div>'
        f'<div style="font-size:12px">'
        f'<span style="color:rgba(255,255,255,0.4)">Streak:</span> '
        f'<strong style="color:#2ecc71">{streak["current"]} 🔥</strong> (Rekord: {streak["longest"]})</div>'
        f'<div style="font-size:11px;color:rgba(255,255,255,0.3);margin-left:auto">'
        f'Fällige Tasks werden täglich automatisch in deine To-Dos gezogen</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    st.markdown("---")

    # ── Tabs ─────────────────────────────────────────────────────
    tab_aufg, tab_neu, tab_coach, tab_heatmap = st.tabs([
        "📋 Aufgaben", "➕ Neue Aufgabe", "🤖 KI Coach", "📅 Konsistenz"
    ])

    with tab_aufg:
        # Alle Frequenzen
        for freq in ['daily', 'weekly', 'monthly', 'custom']:
            tasks_in_freq = [t for t in status_all if t['frequency'] == freq]
            if tasks_in_freq:
                _render_household_section(status_all, freq, today_str)
                st.markdown("")

    with tab_neu:
        st.subheader("✏️ Eigene Haushaltsaufgabe erstellen")
        st.caption("Füge alles hinzu was du in deinem Haushalt machst — die App zieht es dann automatisch in deine To-Dos.")

        with st.form("new_household_task_form", clear_on_submit=True):
            col_icon, col_label = st.columns([0.12, 0.88])
            with col_icon:
                new_icon = st.text_input("Icon", value="🏡", max_chars=4)
            with col_label:
                new_label = st.text_input("Aufgabe*", placeholder="z.B. Auto waschen, Balkon aufräumen, ...")

            col_freq, col_mins = st.columns(2)
            with col_freq:
                new_freq = st.selectbox("Wiederholung", [
                    ('daily',   '📅 Täglich'),
                    ('weekly',  '🗓️ Wöchentlich'),
                    ('monthly', '📆 Monatlich'),
                    ('custom',  '🔧 Eigener Rhythmus'),
                ], format_func=lambda x: x[1])
                freq_key = new_freq[0]
            with col_mins:
                new_mins = st.number_input("Dauer (Minuten)", min_value=1, max_value=180, value=15)

            interval_days = None
            if freq_key == 'custom':
                interval_days = st.number_input(
                    "Alle X Tage", min_value=1, max_value=365, value=14,
                    help="z.B. 14 = alle 2 Wochen, 90 = alle 3 Monate"
                )

            submitted = st.form_submit_button("➕ Aufgabe speichern", use_container_width=True, type="primary")
            if submitted:
                if not new_label.strip():
                    st.error("Bitte einen Namen eingeben.")
                else:
                    add_custom_household_task(
                        label=new_label.strip(),
                        icon=new_icon.strip() or '🏡',
                        frequency=freq_key,
                        est_minutes=int(new_mins),
                        interval_days=int(interval_days) if interval_days else (
                            HOUSEHOLD_FREQUENCY_DAYS.get(freq_key) or 7
                        )
                    )
                    st.success(f"✅ {new_icon} {new_label} gespeichert!")
                    st.rerun()

        # Eigene Aufgaben anzeigen
        custom_status = [t for t in status_all if t.get('is_custom')]
        if custom_status:
            st.markdown("---")
            st.subheader("🔧 Deine eigenen Aufgaben")
            for t in custom_status:
                c1, c2, c3, c4 = st.columns([0.45, 0.27, 0.20, 0.08])
                with c1:
                    freq_txt = (f"alle {t.get('interval_days')}d"
                                if t['frequency'] == 'custom'
                                else HOUSEHOLD_FREQUENCY_LABELS.get(t['frequency'],''))
                    st.markdown(
                        f"{t['icon']} **{t['label']}** "
                        f"<span style='font-size:10px;color:rgba(255,255,255,0.35)'>"
                        f"~{t['est_minutes']} Min · {freq_txt}</span>",
                        unsafe_allow_html=True
                    )
                with c2:
                    st.markdown(_household_status_badge(t), unsafe_allow_html=True)
                with c3:
                    if st.button("✅ Erledigt", key=f"custom_done_{t['key']}_{today_str}", use_container_width=True):
                        log_household_task(t['key'], today_str)
                        st.rerun()
                with c4:
                    if st.button("🗑️", key=f"custom_del_{t['key']}", help="Löschen"):
                        delete_custom_household_task(t['key'])
                        st.rerun()
        else:
            st.info("Noch keine eigenen Aufgaben — erstelle deine erste oben.")

        # Ausgeblendete Built-in-Aufgaben wiederherstellen
        hidden_keys = get_hidden_builtin_keys()
        if hidden_keys:
            st.markdown("---")
            st.subheader("🙈 Ausgeblendete Aufgaben")
            st.caption("Diese Standard-Aufgaben sind ausgeblendet. Klicke auf Wiederherstellen um sie zurückzubringen.")
            hidden_tasks = [t for t in HOUSEHOLD_TASKS if t['key'] in hidden_keys]
            for ht in hidden_tasks:
                hr1, hr2 = st.columns([0.8, 0.2])
                with hr1:
                    freq_label = HOUSEHOLD_FREQUENCY_LABELS.get(ht['frequency'], '')
                    st.markdown(
                        f"{ht['icon']} **{ht['label']}** "
                        f"<span style='font-size:10px;color:rgba(255,255,255,0.35)'>"
                        f"~{ht['est_minutes']} Min · {freq_label}</span>",
                        unsafe_allow_html=True
                    )
                with hr2:
                    if st.button("↩️ Wiederherstellen", key=f"hh_restore_{ht['key']}", use_container_width=True):
                        show_builtin_household_task(ht['key'])
                        st.rerun()

    with tab_coach:
        st.subheader("☕ Haushalts-Pausen heute")
        suggestion = suggest_household_break_tasks()
        wl = suggestion['workload']
        st.caption(f"Zeitbudget: ~{suggestion['budget_minutes']} Min "
                   f"({wl['undone_count']} offene Aufgaben, {wl['deadlines_today']} Deadlines)")
        if suggestion['tasks']:
            for t in suggestion['tasks']:
                col_a, col_b = st.columns([0.8, 0.2])
                with col_a:
                    st.markdown(f"{t['icon']} **{t['label']}** (~{t['est_minutes']} Min)"
                                + (" 🔴 überfällig" if t['overdue'] else ""))
                with col_b:
                    if st.button("✅", key=f"pause_done_{t['key']}", use_container_width=True):
                        log_household_task(t['key'], today_str)
                        st.rerun()
        else:
            st.success("Heute ist nichts dringend fällig — alles im grünen Bereich. 🎉")

        st.markdown("---")
        api_key = get_setting('nvidia_api_key', '')
        if not api_key:
            st.info("Hinterlege einen NVIDIA API-Key in den Einstellungen, um den KI-Coach zu nutzen.")
        else:
            if st.button("🧠 KI-Empfehlung für heute", key="haushalt_coach_btn"):
                with st.spinner("Coach plant deine Pausen…"):
                    st.session_state['_haushalt_coach_result'] = ki_haushalt_coach(api_key)
            result = st.session_state.get('_haushalt_coach_result')
            if result:
                if result.get('error'):
                    st.error(f"Fehler: {result['error']}")
                else:
                    all_key_map = {t['key']: t for t in get_all_household_tasks()}
                    rec_keys = result.get('recommended_keys') or []
                    rec_str = ", ".join(
                        f"{all_key_map[k]['icon']} {all_key_map[k]['label']}"
                        for k in rec_keys if k in all_key_map
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

    with tab_heatmap:
        st.subheader("📅 Konsistenz (letzte 60 Tage)")
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
    sync_household_to_entries()

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

    # ── KI Coach Bar (permanent auf jeder Seite) ─────────────────
    _render_ki_coach_bar()

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
