import pandas as pd
import numpy as np
import urllib.request
import os
import itertools
import math
import plotly.plotly as py
import plotly.graph_objs as go
import datetime
from plotly import tools

def step_MCMC(mat, ref):
    mat0 = mat[mat['trips'] != 0]
    currentrow = mat0.sample()
    currentindex = currentrow.index.values[0]
    proprow = mat.drop(currentindex).sample()
    propindex = proprow.index.values[0]

    currenttrips_mat = currentrow['trips'].values[0]
    proptrips_mat = proprow['trips'].values[0]
    currenttrips_ref = ref.ix[currentindex, 'trips']
    proptrips_ref = ref.ix[propindex, 'trips']

    local_ratio = (currenttrips_ref + proptrips_ref) / (currenttrips_mat + proptrips_mat)

    denom = ((local_ratio*currenttrips_mat-1) - currenttrips_ref)**2 + ((local_ratio*proptrips_mat+1) - proptrips_ref)**2
    num = (local_ratio*currenttrips_mat - currenttrips_ref)**2 + (local_ratio*proptrips_mat - proptrips_ref)**2

    a1 = num / denom

    lpairs = len(mat)
    lpairs0 = len(mat0)
    lpairs0m1 = len(mat0)-1
    lpairs0p1 = len(mat0)+1

    if (currenttrips_mat == 1) and (proptrips_mat) == 0:
        a2 = 1
    elif (currenttrips_mat == 1):
        qxxnew = 1 / (lpairs0*(lpairs-1))
        qxnewx = 1 / (lpairs0m1*(lpairs-1))
        a2 = qxxnew / qxnewx

    elif (proptrips_mat == 0):
        qxxnew = 1 / (lpairs0*(lpairs-1))
        qxnewx = 1 / (lpairs0p1*(lpairs-1))
        a2 = qxxnew / qxnewx

    else:
        a2 = 1

    a = min(1, a1*a2)

    movemade = False

    if (np.random.uniform() < a):
        mat.ix[currentindex,'trips'] -= 1
        mat.ix[propindex, 'trips'] += 1
        movemade = True

    outputdict = dict(
        newmat = mat,
        src = currentindex,
        dest = propindex,
        srctrips = ref.ix[currentindex,'trips'],
        desttrips = ref.ix[propindex,'trips'],
        a1 = a1,
        a2 = a2,
        movemade = movemade
    )

    return outputdict


def mse(mat, ref):
    return ((mat['trips'] - ref['trips'])**2).sum()

def perform_steps(mat, ref, n):

    results = pd.DataFrame(columns = ['src', 'dest', 'a1', 'a2', 'movemade', 'mse'])
    for i in np.arange(0,n):
        output = step_MCMC(mat, ref)
        mat = output['newmat']
        newmse = mse(ref, mat)
        results = pd.concat([results, pd.DataFrame(dict(src = [output['src']], dest = [output['dest']],
                                                      a1 = [output['a1']], a2 = [output['a2']],
                                                      movemade = [output['movemade']], mse = [newmse],
                                                       srctrips = [output['srctrips']],
                                                       desttrips = [output['desttrips']]))],
                            axis=0, ignore_index = True)
        if i % 100 == 0:
            print(str(i) + ': ' + str(newmse))

    return results


def step_MCMC_accept_all(mat, ref):
    mat0 = mat[mat['trips'] != 0]
    currentrow = mat0.sample()
    currentindex = currentrow.index.values[0]
    proprow = mat.drop(currentindex).sample()
    propindex = proprow.index.values[0]

    mat.ix[currentindex,'trips'] -= 1
    mat.ix[propindex, 'trips'] += 1

    return mat


urllib.request.urlretrieve('https://s3.amazonaws.com/tripdata/201607-citibike-tripdata.zip', 'file.zip')
rawbikedata = pd.read_csv('file.zip', compression='zip')
os.remove('file.zip')

for month in ['08', '09']:
    url = 'https://s3.amazonaws.com/tripdata/2016'+month+'-citibike-tripdata.zip'
    urllib.request.urlretrieve(url, 'file.zip')
    rawbikedata = pd.concat([rawbikedata, pd.read_csv('file.zip', compression='zip')], ignore_index=True)
    os.remove('file.zip')

rawbikedata['hour'] = rawbikedata['starttime'].apply(lambda x: int(x[-8:-6]))
rawbikedata['datetime'] = rawbikedata['starttime'].apply(lambda x: datetime.datetime.strptime(x, '%m/%d/%Y %H:%M:%S'))
rawbikedata['dayweek'] = rawbikedata['datetime'].apply(lambda x: x.weekday())
rawbikedata['date'] = rawbikedata['datetime'].apply(lambda x: x.date())
rawbikedata = rawbikedata[rawbikedata['dayweek'].isin([0,1,2,3,4])]

bikedata = rawbikedata[['hour', 'start station id', 'end station id']].reset_index()
bikedata = bikedata.groupby(['hour', 'start station id', 'end station id']).count()
bikedata.columns = ['trips']
bikedata = bikedata.reset_index()

allstations = np.unique(np.concatenate([bikedata['end station id'].unique(),
                                        bikedata['start station id'].unique()], axis=0))
blanklist = pd.DataFrame(list(itertools.product(bikedata['hour'].unique(), allstations, allstations)),
                        columns = ['hour', 'start station id', 'end station id'])

bikedatamatrix = pd.merge(bikedata, blanklist, how='outer', on = ['start station id', 'end station id', 'hour'])
bikedatamatrix['trips'] = bikedatamatrix['trips'].fillna(0)
bikedatamatrix['trips'] = bikedatamatrix['trips'].apply(int)

bikedata = bikedata[bikedata['hour'] == 8].reset_index()

randombikedatamatrix = bikedatamatrix.copy()
for i in np.arange(0,1500):
        randombikedatamatrix = step_MCMC_accept_all(randombikedatamatrix, bikedataslice)
        print(i)

results = perform_steps(randombikedataslice, bikedataslice, 60000)

trace1 = go.Scatter(
    x = results.index.values,
    y = results['mse'],
    name = 'MSE'
)

trace2 = go.Histogram(
    x = results['mse'],
    name = 'MSE Distribution',
    xbins = dict(
        start = 0,
        end = 400,
        size = 2
    )
)

fig = tools.make_subplots(rows=2, cols=1)

fig.append_trace(trace1, 1, 1)
fig.append_trace(trace2, 2, 1)


py.plot(fig, filename = 'section 1 citibike')
