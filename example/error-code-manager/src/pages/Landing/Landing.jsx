import React from 'react';
import './landing.css'

const Landing = (props) => {
    return (
        <div className={"landing"}>
            <h1 style={{color: "var(--green)", fontSize: "5rem", lineHeight: "1rem"}}>Oh no!</h1>
            <h5 style={{fontFamily: "Silkscreen"}}>AN ERROR OCCURED</h5>
            <img className={"landing-img"} src={process.env.PUBLIC_URL + '/img/warning.png'} alt='404' />
        </div>
    );
}

export default Landing;
