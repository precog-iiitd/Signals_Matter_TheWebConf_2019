import sys
import os
import pickle
import math
import datetime
from multiprocessing import Pool
import numpy as np
import pandas as pd
import sklearn
from xgboost import XGBRegressor
from sklearn.metrics import r2_score, explained_variance_score
from imblearn.metrics import classification_report_imbalanced

################################################################################
################################################################################
################################################################################

df = pd.read_csv("../data/augmented_small_df.csv")
df = df[ (df.num_questions > 0) | (df.num_answers > 0) | (df.num_comments > 0)]

base_features = [ 'int_1e6_log_days_since_join', 'int_1e6_log_days_since_last_access', 'num_questions', 'num_answers', 'num_comments', 'up_votes', 'down_votes' ]

reputation_features = [ 'reputation' ]

question_badge_features = ['num_Altruist_badges', 'num_Benefactor_badges', 'num_Curious_badges', 'num_Inquisitive_badges', 'num_Socratic_badges', 'num_Favorite_Question_badges', 'num_Stellar_Question_badges',  'num_Investor_badges',  'num_Nice_Question_badges', 'num_Good_Question_badges', 'num_Great_Question_badges', 'num_Popular_Question_badges', 'num_Notable_Question_badges', 'num_Famous_Question_badges', 'num_Promoter_badges', 'num_Scholar_badges', 'num_Student_badges', 'num_Tumbleweed_badges']

answer_badge_features = ['num_Enlightened_badges', 'num_Explainer_badges', 'num_Refiner_badges', 'num_Illuminator_badges', 'num_Generalist_badges', 'num_Guru_badges', 'num_Nice_Answer_badges', 'num_Good_Answer_badges', 'num_Great_Answer_badges', 'num_Populist_badges', 'num_Reversal_badges', 'num_Revival_badges', 'num_Necromancer_badges', 'num_Self_Learner_badges', 'num_Teacher_badges', 'num_Tenacious_badges', 'num_Unsung_Hero_badges']

moderation_badge_features = ['num_Citizen_Patrol_badges', 'num_Deputy_badges', 'num_Marshall_badges', 'num_Civic_Duty_badges', 'num_Cleanup_badges', 'num_Constable_badges', 'num_Sheriff_badges', 'num_Critic_badges', 'num_Custodian_badges', 'num_Reviewer_badges', 'num_Steward_badges', 'num_Disciplined_badges', 'num_Editor_badges', 'num_Strunk_White_badges', 'num_Copy_Editor_badges', 'num_Electorate_badges', 'num_Excavator_badges', 'num_Archaeologist_badges', 'num_Organizer_badges', 'num_Peer_Pressure_badges', 'num_Proofreader_badges', 'num_Sportsmanship_badges', 'num_Suffrage_badges', 'num_Supporter_badges', 'num_Synonymizer_badges', 'num_Tag_Editor_badges', 'num_Research_Assistant_badges', 'num_Taxonomist_badges', 'num_Vox_Populi_badges']

participation_badge_features = ['num_Autobiographer_badges', 'num_Caucus_badges', 'num_Constituent_badges', 'num_Commentator_badges', 'num_Pundit_badges', 'num_Enthusiast_badges', 'num_Fanatic_badges', 'num_Mortarboard_badges', 'num_Epic_badges', 'num_Legendary_badges', 'num_Precognitive_badges', 'num_Beta_badges', 'num_Quorum_badges', 'num_Convention_badges', 'num_Talkative_badges', 'num_Outspoken_badges', 'num_Yearling_badges']

other_badge_features = ['num_Analytical_badges', 'num_Announcer_badges', 'num_Booster_badges', 'num_Publicist_badges', 'num_Census_badges', 'num_resultsrmed_badges', 'num_Not_a_Robot_badges']

documentation_badge_features = ['num_Documentation_Beta_badges', 'num_Documentation_Pioneer_badges', 'num_Documentation_User_badges']

badge_features = question_badge_features + answer_badge_features + moderation_badge_features + participation_badge_features + other_badge_features + documentation_badge_features

################################################################################
################################################################################
################################################################################

def run_model(feature_set, predict_feature, num_runs):
    return p.map(regression, [ (x, XGBRegressor(), feature_set, predict_feature) for x in range(num_runs) ])

def likelhood_aic_bic(y_true, y_pred, num_vars, num_obs):
    resid = y_true - y_pred
    sse = sum(resid**2)
    aic = 2*num_vars - 2*np.log(sse)
    bic = num_obs*np.log(sse/num_obs) + num_vars*np.log(num_obs)
    return np.log(sse), aic, bic

def regression(x):
    idx, model, fvars, pvars = x
    model.fit(df[fvars], df[pvars])
    y_pred = model.predict(df[fvars])
    y_true = df[pvars]
    log_likelihood, aic, bic = likelhood_aic_bic(y_true, y_pred, len(fvars), len(df))
    report = [ r2_score(y_true, y_pred), explained_variance_score(y_true, y_pred), aic, bic, log_likelihood ]
    return (model, report)

def get_metrics_regression(results, num_runs):
    r2 =      [ results[i][1][0] for i in range(num_runs) ]
    exp_var = [ results[i][1][1] for i in range(num_runs) ]
    aic =     [ results[i][1][2] for i in range(num_runs) ]
    bic =     [ results[i][1][3] for i in range(num_runs) ]
    log_lik = [ results[i][1][4] for i in range(num_runs) ]
    return {"r2" : r2, "exp_var": exp_var, "aic" : aic, "bic" : bic, "log_likelihood": log_lik }

def metric_average(metrics, num_runs):
    return sum(metrics)/num_runs

def print_metrics(results, num_runs):
    metrics = get_metrics_regression(results, num_runs)
    for k, v in metrics.items():
        print(k, round(metric_average(v, num_runs), 5))

def get_feature_importances(results, num_runs, relative=False):
    feature_importance = np.average(np.array([ results[i][0].feature_importances_ for i in xrange(num_runs)]), axis=0)
    if relative:
        feature_importance = 100.0 * (feature_importance / feature_importance.max())
    return feature_importance

def print_feature_importances(results, feature_set, num_runs, relative=False):
    feature_importance = get_feature_importances(results, num_runs, relative=relative)
    print_vals = sorted(zip(feature_set, feature_importance), key=lambda x: x[1], reverse=True)
    for k,v in print_vals:
        print(k, round(v, 5))

if __name__=="__main__":
    if sys.argv[1] == 'popularity':
        predict_feature = 'z_score_views'
    elif sys.argv[1] == 'impact':
        predict_feature = 'z_score_impact'
    else:
        print("Choose between 'popularity' and 'impact'.")
        exit()

    if sys.argv[2] == 'base':
        model_name = 'Base_Model'
        feature_set = base_features
    elif sys.argv[2] == 'reputation':
        model_name = 'Reputation_Model'
        feature_set = base_features + reputation_features
    if sys.argv[2] == 'badges':
        model_name == 'Badges_Model'
        feature_set = base_features + badge_features
    else:
        print("Choose between 'base', 'reputation', and 'badges'.")
        exit()

    num_runs = sys.argv[3]
    num_threads = sys.argv[4]

    fname = "../data/" + predict_feature + "_" + model_name + "_report.pkl"

    p = Pool(num_threads)
    if not os.path.exists(fname):
        results = run_model(feature_set, predict_feature, num_runs)
        with open(fname, 'wb') as f:
            pickle.dump(results, f)

    with open(fname, 'rb') as f:
        results = pickle.load(f)

    print_metrics(results, num_runs)
    print_feature_importances(results, num_runs, feature_set, relative=False) 
