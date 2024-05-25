import React, { useState } from 'react';
import { Link, useLocation } from "react-router-dom";
import { PiSealQuestionFill, PiBalloonFill } from "react-icons/pi";
import { TbTimelineEventFilled } from "react-icons/tb";
import { useEffect } from 'react';
import './navbar.css';

const NavElement = (props) => {
  const [status, setStatus] = useState(props.status);
  const location = useLocation();
  useEffect(() => {
    if(location.pathname.startsWith(props.link) && (props.link !== "/" || location.pathname === props.link)) setStatus("selected");
    else setStatus("none");
  }, [location, props.link]);
  return (
    <Link to={props.link} onClick={() => {setStatus("routed")}}>
      <div className="nav-element prevent-select" status={status}>
        <div className="icon-container">{ props.children }</div>
        <div className="text-container"><p> { props.text } </p></div>
      </div>
    </Link>
  );
}

const Navbar = (props) => {
    return (
        <nav>
            <NavElement text={"Home"} link={"/"}><PiBalloonFill size={'2rem'}/></NavElement>
            <NavElement text={"What the Error?!"} link={"/wtf"}><PiSealQuestionFill size={'2rem'}/></NavElement>
            <NavElement text={"Log"} link={"/log"}><TbTimelineEventFilled size={'2rem'}/></NavElement>
        </nav>
    );
}

export default Navbar;
