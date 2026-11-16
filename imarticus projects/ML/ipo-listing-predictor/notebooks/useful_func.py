import pandas as pd
import numpy as np
from sklearn.metrics import r2_score, mean_absolute_error


def missing_info(df):
  """
  Generate a summary of missing values for each column in a DataFrame.

  This function calculates the total number of missing values and the
  percentage of missing values for each column. Only columns with at least
  one missing value are included in the output. The result is sorted in
  descending order based on the number of missing values.

  Parameters
  ----------
  df : pandas.DataFrame
      Input DataFrame for which missing value statistics are required.

  Returns
  -------
  pandas.DataFrame
      A DataFrame containing:
      - column_name : Name of the column
      - num_missing : Total number of missing values in the column
      - missing%    : Percentage of missing values in the column

      The output is sorted by `num_missing` in descending order and
      indexed from 0.

  Examples
  --------
  >>> missing_info(df)
      column_name  num_missing  missing%
  0      age             15        7.50
  1      salary          10        5.00
  """
  result = pd.DataFrame({
      'column_name': df.columns,
      'num_missing': df.isnull().sum(),
      'missing%': np.round((df.isnull().mean() * 100),2)
  })
  result = result[result['num_missing'] > 0]
  result = result.sort_values(by=['num_missing'], ascending=False)
  result = result.reset_index(drop=True)

  return result



def out_info(df, thresh = 0.5):
  """
    Identify outliers in numerical columns using Z-score or IQR based on skewness.

    This function detects outliers for each numerical column in a DataFrame.
    The method used depends on the column's skewness:
    - Z-score method is applied when absolute skewness is less than or equal
      to the specified threshold (approximately symmetric distribution).
    - IQR method is applied when absolute skewness exceeds the threshold
      (skewed distribution).

    Only columns containing at least one outlier are included in the output.
    The results are sorted in descending order based on the number of outliers.

    Parameters
    ----------
    df : pandas.DataFrame
        Input DataFrame containing numerical and categorical columns.

    thresh : float, default=0.5
        Skewness threshold used to decide the outlier detection method.
        Columns with |skewness| <= thresh use Z-score,
        otherwise IQR is applied.

    Returns
    -------
    pandas.DataFrame
        A DataFrame containing outlier information with the following columns:
        - col_name : Name of the numerical column
        - method   : Outlier detection method used ("z_score" or "iqr")
        - num_out  : Number of detected outliers
        - out_%    : Percentage of outliers in the column
        - ul       : Upper limit used for outlier detection
        - ll       : Lower limit used for outlier detection

        The output is sorted by `num_out` in descending order and
        reindexed from 0.

    Notes
    -----
    - Z-score uses ±3 standard deviations from the mean.
    - IQR uses 1.5 × IQR beyond the first and third quartiles.
    - Categorical (object dtype) columns are ignored.

    Examples
    --------
    >>> out_info(df)
        col_name  method   num_out  out_%     ul       ll
    0    salary    iqr        12    3.45   250000   -5000
    1    age       z_score     5    1.20     78.4     12.1
    """


  num_cols = [col for col in df.columns if df[col].dtype != "object"]
  result_df = pd.DataFrame({
      "col_name":[],
      "method":[],
      "num_out":[],
      "out_%":[],
      "ul":[],
      "ll":[]
  })
  index = 0
  for col in num_cols:
    col_skew = df[col].skew()
    if abs(col_skew) <= thresh:
      # zscore method
      col_mean = df[col].mean()
      col_std = df[col].std()
      ul = col_mean + 3* col_std
      ll = col_mean - 3* col_std
      mask = (df[col] > ul) | (df[col] < ll)
      num_out = mask.sum()
      per_out = round(mask.mean()*100,2)

      result_df.loc[index] = [col, "z_score", num_out, per_out, ul, ll]
      index +=1
    else:
      #iqr method
      q1 = df[col].quantile(0.25)
      q3 = df[col].quantile(0.75)
      iqr = q3 - q1
      ul = q3 + 1.5*iqr
      ll = q1 - 1.5*iqr
      mask = (df[col] > ul) | (df[col] < ll)
      num_out = mask.sum()
      per_out = round(mask.mean()*100,2)

      result_df.loc[index] = [col, "iqr", num_out, per_out, ul, ll]
      index +=1

  mask = result_df["num_out"] > 0
  result_df = result_df[mask]
  result_df.sort_values(by = "num_out",
                        ascending = False, inplace = True)
  
  result_df.reset_index(drop = True, inplace = True)
  return result_df


result_df = pd.DataFrame({
    "method":[],

    "mean_train_acc":[],
    "mean_valid_acc":[],
    "std_train_acc":[],
    "std_valid_acc":[],

    "mean_train_precision":[],
    "mean_valid_precision":[],
    "std_train_precision":[],
    "std_valid_precision":[],

    "mean_train_recall":[],
    "mean_valid_recall":[],
    "std_train_recall":[],
    "std_valid_recall":[],

    "mean_train_f1":[],
    "mean_valid_f1":[],
    "std_train_f1":[],
    "std_valid_f1":[],
})

from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
def classification_eval(method, model, X_train, y_train, fold = 5,
                        result_df = result_df):

  """
    Perform stratified k-fold cross-validation for a classification model and
    compute evaluation metrics on both training and validation folds.

    The function trains the given model using StratifiedKFold cross-validation
    and calculates the mean and standard deviation of the following metrics
    across folds:
        - Accuracy
        - Precision
        - Recall
        - F1-score

    Results are appended as a new row to the provided result DataFrame.

    Parameters
    ----------
    method : str
        Name or description of the modeling approach (e.g., 'Logistic Regression',
        'Random Forest with SMOTE'). This is stored in the results table.

    model : sklearn estimator
        A scikit-learn compatible classification model implementing
        `fit()` and `predict()` methods.

    X_train : pandas.DataFrame
        Training feature matrix.

    y_train : pandas.Series or pandas.DataFrame
        Target labels corresponding to `X_train`.

    fold : int, default=5
        Number of stratified folds to use in cross-validation.

    result_df : pandas.DataFrame
        DataFrame used to store evaluation results. A new row containing
        aggregated metrics for the given method is appended to this DataFrame.

    Returns
    -------
    pandas.DataFrame
        Updated results DataFrame with one additional row containing:
            - Mean and standard deviation of training and validation accuracy
            - Mean and standard deviation of training and validation precision
            - Mean and standard deviation of training and validation recall
            - Mean and standard deviation of training and validation F1-score

    Notes
    -----
    - StratifiedKFold is used to preserve class distribution across folds.
    - Precision, recall, and F1-score assume a binary classification problem
      with the positive class labeled as `1`.
    - Metrics are computed using model predictions (`predict`), not probabilities.
    """
  skf = StratifiedKFold(n_splits = fold)
  train_acc = []
  valid_acc = []

  train_precision = []
  valid_precision = []

  train_recall = []
  valid_recall = []

  train_f1 = []
  valid_f1 = []

  for i, (train_index, valid_index) in enumerate(skf.split(X_train, y_train)):
    X_train_fold = X_train.iloc[train_index]
    y_train_fold = y_train.iloc[train_index]

    X_valid_fold = X_train.iloc[valid_index]
    y_valid_fold = y_train.iloc[valid_index]

    model.fit(X_train_fold, y_train_fold)
    y_pred_train_fold = model.predict(X_train_fold)
    y_pred_valid_fold = model.predict(X_valid_fold)

    train_acc.append(accuracy_score(y_train_fold, y_pred_train_fold))
    valid_acc.append(accuracy_score(y_valid_fold, y_pred_valid_fold))

    train_precision.append(precision_score(y_train_fold, y_pred_train_fold))
    valid_precision.append(precision_score(y_valid_fold, y_pred_valid_fold))

    train_recall.append(recall_score(y_train_fold, y_pred_train_fold))
    valid_recall.append(recall_score(y_valid_fold, y_pred_valid_fold))

    train_f1.append(f1_score(y_train_fold, y_pred_train_fold))
    valid_f1.append(f1_score(y_valid_fold, y_pred_valid_fold))

  mean_train_acc = np.mean(train_acc)
  mean_valid_acc = np.mean(valid_acc)
  std_train_acc = np.std(train_acc)
  std_valid_acc = np.std(valid_acc)

  mean_train_precision = np.mean(train_precision)
  mean_valid_precision = np.mean(valid_precision)
  std_train_precision = np.std(train_precision)
  std_valid_precision = np.std(valid_precision)

  mean_train_recall = np.mean(train_recall)
  mean_valid_recall = np.mean(valid_recall)
  std_train_recall = np.std(train_recall)
  std_valid_recall = np.std(valid_recall)

  mean_train_f1 = np.mean(train_f1)
  mean_valid_f1 = np.mean(valid_f1)
  std_train_f1 = np.std(train_f1)
  std_valid_f1 = np.std(valid_f1)

  row_num = len(result_df)
  result_df.loc[row_num] = [method,
                            mean_train_acc, mean_valid_acc, std_train_acc, std_valid_acc,
                            mean_train_precision, mean_valid_precision, std_train_precision, std_valid_precision,
                            mean_train_recall, mean_valid_recall, std_train_recall, std_valid_recall,
                            mean_train_f1, mean_valid_f1, std_train_f1, std_valid_f1]

  return result_df

  

def regression_eval(method, X, y, model,
                    result_reg_df=None,
                    n_splits=5):
    """
    Perform K-Fold cross-validation for a regression model and compute
    train and validation performance metrics.

    This function evaluates a regression model using K-Fold cross-validation
    and returns aggregated metrics including Mean Absolute Error (MAE),
    R-squared (R²), and Adjusted R-squared for both training and validation
    sets. The results are appended to a summary DataFrame for easy
    comparison across multiple models or methods.

    Parameters
    ----------
    method : str
        Name or description of the regression method or feature-engineering
        technique being evaluated (e.g., 'Linear Regression', 'Ridge + Scaling').

    X : pandas.DataFrame
        Feature matrix containing predictor variables.

    y : pandas.Series or pandas.DataFrame
        Target variable corresponding to the feature matrix.

    model : sklearn-compatible estimator
        Any regression model implementing `fit()` and `predict()` methods
        (e.g., LinearRegression, RandomForestRegressor, XGBRegressor).

    result_reg_df : pandas.DataFrame, optional (default=None)
        DataFrame used to store and accumulate evaluation results.
        If None, a new DataFrame is created.

    n_splits : int, optional (default=5)
        Number of folds to use in K-Fold cross-validation.

    Returns
    -------
    pandas.DataFrame
        Updated DataFrame containing the following columns:
        - method
        - train_mae
        - valid_mae
        - train_r2
        - valid_r2
        - train_adj_r2
        - valid_adj_r2

    Notes
    -----
    - K-Fold cross-validation is performed with shuffling enabled to reduce
      bias due to ordered data.
    - Adjusted R² is computed only when the number of samples is greater
      than the number of features plus one; otherwise, NaN is returned.
    - Metrics are averaged across all folds.

    Examples
    --------
    >>> result_reg_df = regression_eval(
    ...     method="Linear Regression",
    ...     X=X_train,
    ...     y=y_train,
    ...     model=LinearRegression(),
    ...     result_reg_df=result_reg_df
    ... )
    """

    if result_reg_df is None:
        result_reg_df = pd.DataFrame({
            "method": [],
            "train_mae": [],
            "valid_mae": [],
            "train_r2": [],
            "valid_r2": [],
            "train_adj_r2": [],
            "valid_adj_r2": []
        })

    train_mae_list, valid_mae_list = [], []
    train_r2_list, valid_r2_list = [], []
    train_adj_r2_list, valid_adj_r2_list = [], []

    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)

    for train_idx, valid_idx in kf.split(X, y):
        X_train, X_valid = X.iloc[train_idx], X.iloc[valid_idx]
        y_train, y_valid = y.iloc[train_idx], y.iloc[valid_idx]

        model.fit(X_train, y_train)

        y_train_pred = model.predict(X_train)
        y_valid_pred = model.predict(X_valid)

        train_mae_list.append(mean_absolute_error(y_train, y_train_pred))
        valid_mae_list.append(mean_absolute_error(y_valid, y_valid_pred))

        train_r2 = r2_score(y_train, y_train_pred)
        valid_r2 = r2_score(y_valid, y_valid_pred)

        train_r2_list.append(train_r2)
        valid_r2_list.append(valid_r2)

        n, k = X_train.shape
        n1, k1 = X_valid.shape

        train_adj_r2 = np.nan if n <= k + 1 else 1 - ((1 - train_r2) * (n - 1) / (n - k - 1))
        valid_adj_r2 = np.nan if n1 <= k1 + 1 else 1 - ((1 - valid_r2) * (n1 - 1) / (n1 - k1 - 1))

        train_adj_r2_list.append(train_adj_r2)
        valid_adj_r2_list.append(valid_adj_r2)

    result_reg_df.loc[len(result_reg_df)] = [
        method,
        np.mean(train_mae_list),
        np.mean(valid_mae_list),
        np.mean(train_r2_list),
        np.mean(valid_r2_list),
        np.nanmean(train_adj_r2_list),
        np.nanmean(valid_adj_r2_list)
    ]

    return result_reg_df