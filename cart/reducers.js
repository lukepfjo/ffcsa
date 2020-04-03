// inspired by https://github.com/matthiask/workbench/tree/39a4287b45fc7a1b59a3eb9dfd9f11ef461c3834

import { combineReducers } from 'redux'

function activities (state = {}, action) {
  switch (action.type) {
    // case "ADD_ACTIVITY":
    //   return {...state, [action.activity.id]: action.activity}
    // case "REMOVE_ACTIVITY":
    //   return Object.fromEntries(
    //     Object.entries(state).filter(([id]) => id != action.id)
    //   )
    // case "UPDATE_ACTIVITY":
    //   return {
    //     ...state,
    //     [action.id]: {
    //       ...state[action.id],
    //       ...action.fields,
    //     },
    //   }
    default:
      return state
  }
}

const reducers = combineReducers({
  activities,
})

export default reducers
