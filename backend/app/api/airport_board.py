from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import get_current_user
from app.research_agent.tools.cirium_tool import get_airport_board
from app.agents.workflow import resolve_runway_availability

router = APIRouter(prefix='/api/airport-board', dependencies=[Depends(get_current_user)])

@router.get('/{airport}')
def board(airport: str):
    airport = airport.upper()
    if airport not in {'DEL', 'VIDP'}:
        raise HTTPException(400, 'Only DEL is supported for this board.')
    return get_airport_board(airport)

@router.get('/{airport}/runways')
def runways(airport: str):
    if airport.upper() not in {'DEL', 'VIDP'}:
        raise HTTPException(400, 'Only DEL is supported for this board.')
    return {'runways': [{'code': code, **resolve_runway_availability('DEL', code)}
                        for code in ('09/27', '10/28', '11L/29R', '11R/29L')],
            'note': 'Manual advisory reports only; not official ATC status.'}
