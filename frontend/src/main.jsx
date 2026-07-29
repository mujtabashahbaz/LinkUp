import React, {useEffect, useState} from "react";
import {createRoot} from "react-dom/client";
import "./styles.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function api(path, options={}) {
  const token = localStorage.getItem("token");
  const headers = {...(options.headers || {})};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
  const r = await fetch(API + path, {...options, headers});
  if (!r.ok) {
    let msg = "Request failed";
    try { msg = (await r.json()).detail || msg; } catch {}
    throw new Error(msg);
  }
  return r.json();
}

const initials = n => (n || "?").split(" ").map(x=>x[0]).slice(0,2).join("").toUpperCase();

function Avatar({user, large=false}) {
  if (user?.avatar) return <img className={large ? "avatar large":"avatar"} src={user.avatar} />;
  return <div className={large ? "avatar large initials":"avatar initials"}>{initials(user?.name)}</div>;
}

function Auth({onAuth}) {
  const [register, setRegister] = useState(false);
  const [form, setForm] = useState({name:"",email:"",password:""});
  const [error,setError] = useState("");
  async function submit(e) {
    e.preventDefault(); setError("");
    try {
      let data;
      if (register) {
        data = await api("/auth/register",{method:"POST",body:JSON.stringify(form)});
      } else {
        const body = new URLSearchParams({username:form.email,password:form.password});
        data = await api("/auth/login",{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body});
      }
      localStorage.setItem("token", data.access_token); onAuth(data.user);
    } catch(e) { setError(e.message); }
  }
  return <div className="auth-page">
    <div className="brand big">Link<span>Up</span></div>
    <div className="auth-card">
      <h1>{register ? "Make the most of your professional life" : "Sign in"}</h1>
      <form onSubmit={submit}>
        {register && <input placeholder="Full name" value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/>}
        <input type="email" placeholder="Email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/>
        <input type="password" placeholder="Password" value={form.password} onChange={e=>setForm({...form,password:e.target.value})}/>
        {error && <div className="error">{error}</div>}
        <button className="primary">{register ? "Agree & Join" : "Sign in"}</button>
      </form>
      <p className="center">{register ? "Already on LinkUp?" : "New to LinkUp?"} <button className="link" onClick={()=>setRegister(!register)}>{register ? "Sign in":"Join now"}</button></p>
    </div>
  </div>
}

function Header({me, setPage, logout}) {
  return <header>
    <div className="header-inner">
      <button className="brand compact" onClick={()=>setPage("feed")}>in</button>
      <input className="search" placeholder="Search professionals" onFocus={()=>setPage("network")}/>
      <nav>
        <button onClick={()=>setPage("feed")}>⌂<small>Home</small></button>
        <button onClick={()=>setPage("network")}>♟<small>My Network</small></button>
        <button onClick={()=>setPage("profile")}>●<small>Me</small></button>
        <button onClick={logout}>↪<small>Sign out</small></button>
      </nav>
    </div>
  </header>
}

function ProfileCard({me, setPage}) {
  return <div className="card profile-mini">
    <div className="cover"></div><Avatar user={me} large/>
    <button className="profile-link" onClick={()=>setPage("profile")}><b>{me.name}</b></button>
    <div className="muted">{me.headline}</div><div className="muted small">{me.location}</div>
  </div>
}

function Feed({me, setPage}) {
  const [posts,setPosts]=useState([]), [body,setBody]=useState("");
  const load=()=>api("/feed").then(setPosts);
  useEffect(()=>{load()},[]);
  async function post(){ if(!body.trim()) return; await api("/posts",{method:"POST",body:JSON.stringify({body})});setBody("");load();}
  async function like(id){await api(`/posts/${id}/like`,{method:"POST"});load();}
  async function comment(id,e){e.preventDefault();const v=e.target.elements.comment.value;if(!v.trim())return;await api(`/posts/${id}/comments`,{method:"POST",body:JSON.stringify({body:v})});e.target.reset();load();}
  return <main className="layout">
    <aside><ProfileCard me={me} setPage={setPage}/></aside>
    <section>
      <div className="card composer">
        <div className="row"><Avatar user={me}/><button className="start-post" onClick={()=>document.getElementById("postbox").focus()}>Start a post</button></div>
        <textarea id="postbox" placeholder="Share an update..." value={body} onChange={e=>setBody(e.target.value)}/>
        <button className="primary post-btn" onClick={post}>Post</button>
      </div>
      {posts.map(p=><article className="card post" key={p.id}>
        <div className="post-head"><Avatar user={p.author}/><div><b>{p.author.name}</b><div className="muted small">{p.author.headline}</div><div className="muted tiny">{new Date(p.created_at).toLocaleString()}</div></div></div>
        <div className="post-body">{p.body}</div>
        <div className="social-count">{p.likes} like{p.likes!==1?"s":""} · {p.comments.length} comment{p.comments.length!==1?"s":""}</div>
        <div className="actions"><button onClick={()=>like(p.id)}>{p.liked?"♥":"♡"} Like</button><button onClick={e=>e.currentTarget.closest("article").querySelector("input").focus()}>◯ Comment</button></div>
        <div className="comments">
          {p.comments.map(c=><div className="comment" key={c.id}><Avatar user={c.author}/><div className="bubble"><b>{c.author.name}</b><div>{c.body}</div></div></div>)}
          <form className="comment-form" onSubmit={e=>comment(p.id,e)}><Avatar user={me}/><input name="comment" placeholder="Add a comment..."/></form>
        </div>
      </article>)}
    </section>
    <aside><div className="card news"><h3>LinkUp News</h3><b>Build your professional network</b><p className="muted">Connect with people and share what you're working on.</p><b>Skills are the new currency</b><p className="muted">Keep learning and keep growing.</p></div></aside>
  </main>
}

function Network() {
  const [users,setUsers]=useState([]);
  const load=()=>api("/users").then(setUsers);
  useEffect(()=>{load()},[]);
  async function action(u){
    if(u.connection?.incoming) await api(`/connections/${u.connection.id}/accept`,{method:"POST"});
    else await api(`/connections/${u.id}`,{method:"POST"});
    load();
  }
  return <main className="single"><div className="card network"><h2>People you may know</h2><div className="people">
    {users.map(u=><div className="person" key={u.id}><div className="person-cover"></div><Avatar user={u} large/><b>{u.name}</b><div className="muted">{u.headline || "Professional"}</div><div className="muted small">{u.location}</div>
      {u.connection?.status==="accepted" ? <button disabled>Connected</button> :
       u.connection && !u.connection.incoming ? <button disabled>Pending</button> :
       <button onClick={()=>action(u)}>{u.connection?.incoming?"Accept":"Connect"}</button>}
    </div>)}
  </div></div></main>
}

function Profile({me,setMe}) {
  const [edit,setEdit]=useState(false), [form,setForm]=useState(me);
  async function save(e){e.preventDefault();const u=await api("/me",{method:"PUT",body:JSON.stringify(form)});setMe(u);setEdit(false);}
  return <main className="single"><div className="card profile-page"><div className="profile-cover"></div><Avatar user={me} large/>
    {!edit ? <><button className="edit" onClick={()=>setEdit(true)}>✎ Edit profile</button><h1>{me.name}</h1><h3>{me.headline}</h3><div className="muted">{me.location}</div><hr/><h2>About</h2><p>{me.about || "Add an about section to tell people about yourself."}</p></> :
    <form className="profile-form" onSubmit={save}><h2>Edit profile</h2>
      {["name","headline","location","avatar"].map(k=><label key={k}>{k[0].toUpperCase()+k.slice(1)}<input value={form[k]||""} onChange={e=>setForm({...form,[k]:e.target.value})}/></label>)}
      <label>About<textarea value={form.about||""} onChange={e=>setForm({...form,about:e.target.value})}/></label>
      <div className="row end"><button type="button" onClick={()=>setEdit(false)}>Cancel</button><button className="primary">Save</button></div>
    </form>}
  </div></main>
}

function App(){
  const [me,setMe]=useState(null),[page,setPage]=useState("feed"),[loading,setLoading]=useState(true);
  useEffect(()=>{if(localStorage.getItem("token")) api("/me").then(setMe).catch(()=>localStorage.removeItem("token")).finally(()=>setLoading(false));else setLoading(false)},[]);
  if(loading)return <div className="loading">Loading…</div>;
  if(!me)return <Auth onAuth={setMe}/>;
  const logout=()=>{localStorage.removeItem("token");setMe(null)};
  return <><Header me={me} setPage={setPage} logout={logout}/>{page==="feed"?<Feed me={me} setPage={setPage}/>:page==="network"?<Network/>:<Profile me={me} setMe={setMe}/>}</>
}
createRoot(document.getElementById("root")).render(<App/>);
